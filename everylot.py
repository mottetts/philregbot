#!/usr/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import sqlite3
import logging
from io import BytesIO
import requests

QUERY = """SELECT
    *
    FROM lots
    where {} = ? and ({} not in (?,?) or {} not in (?,?))
    ORDER BY random()
    LIMIT 1;
"""

SVAPI = "https://maps.googleapis.com/maps/api/streetview"
GCAPI = "https://maps.googleapis.com/maps/api/geocode/json"


class EveryLot(object):

    def __init__(self, database,
                 search_format=None,
                 id_=None,
                 **kwargs):
        """
        An everylot class immediately checks the database for the next available entry,
        or for the passed 'id_'. It stores this data in self.lot.
        :database str file name of database
        """
        # os.chdir('C://Users//Christopher//everylot//everylotbot')
        
        self.logger = kwargs.get('logger', logging.getLogger('everylot'))

        # set address format for fetching from DB
        self.search_format = search_format or '{address}, Philadelphia, PA {zip}'

        self.logger.debug('searching google sv with %s', self.search_format)
        
        self.conn = sqlite3.connect(database)

        # filtered = "('','pending')"
        
        if id_:
            field = 'id'
            value = id_
        else:
            field = 'tweeted'
            value = 0

        curs = self.conn.execute(QUERY.format(field,'desigdate','districtdate'), (value,'','pending','','pending'))
        keys = [c[0] for c in curs.description]
        self.lot = dict(zip(keys, curs.fetchone()))

    def aim_camera(self):
        '''Set field-of-view and pitch'''
        fov, pitch = 65, 10
        try:
            floors = float(self.lot.get('num_stories', 0)) or 2
        except TypeError:
            floors = 2

        if floors == 3:
            fov = 72

        if floors == 4:
            fov, pitch = 76, 15

        if floors >= 5:
            fov, pitch = 81, 20

        if floors == 6:
            fov = 86

        if floors >= 8:
            fov, pitch = 90, 25

        if floors >= 10:
            fov, pitch = 90, 30

        return fov, pitch

    def get_streetview_image(self, key):
        '''Fetch image from streetview API'''
        params = {
            "location": self.streetviewable_location(key),
            "key": key,
            "size": "1000x1000"
        }

        params['fov'], params['pitch'] = self.aim_camera()

        r = requests.get(SVAPI, params=params)
        self.logger.debug(r.url)

        sv = BytesIO()
        for chunk in r.iter_content():
            sv.write(chunk)

        sv.seek(0)
        return sv

    def streetviewable_location(self, key):
        '''
        Check if google-geocoded address is nearby or not. if not, use the lat/lon
        '''
        # skip this step if there's no address, we'll just use the lat/lon to fetch the SV.
        try:
            address = self.search_format.format(**self.lot)

        except KeyError:
            self.logger.warn('Could not find street address, using lat/lon')
            return '{},{}'.format(self.lot['lat'], self.lot['lon'])

        # bounds in (miny minx maxy maxx) aka (s w n e)
        try:
            d = 0.007
            minpt = self.lot['lat'] - d, self.lot['lon'] - d
            maxpt = self.lot['lat'] + d, self.lot['lon'] + d

        except (KeyError,TypeError):
            self.logger.info('Could not find lat/lon coordinates. Using address naively.')
            return address

        params = {
            "address": address,
            "key": key,
        }

        self.logger.debug('geocoding @ google')

        try:
            r = requests.get(GCAPI, params=params)
            self.logger.debug(r.url)

            if r.status_code != 200:
                raise ValueError('bad response from google geocode: %s' % r.status_code)

            loc = r.json()['results'][0]['geometry']['location']

            # Cry foul if we're outside of the bounding box
            outside_comfort_zone = any((
                loc['lng'] < minpt[1],
                loc['lng'] > maxpt[1],
                loc['lat'] > maxpt[0],
                loc['lat'] < minpt[0]
            ))

            if outside_comfort_zone:
                raise ValueError('google geocode puts us outside outside our comfort zone')

            self.logger.debug('using db address for sv')
            return address

        except Exception as e:
            self.logger.info(e)
            self.logger.info('location with db coords: %s, %s', self.lot['lat'], self.lot['lon'])
            return '{},{}'.format(self.lot['lat'], self.lot['lon'])

    def write_tweet(self):
        '''
        Format the text of the tweet, which should at minimum include an address and date of 
        designation. Optional details are historic name, date built, historic district and 
        district designation date.
        '''
        
        tweet = ''
        
        if self.lot['official_yn'] == 'Y':
            tweet = (self.lot['address']).title()
        
        if self.lot['histname'] != '':
            tweet += '\n{}'.format(self.lot['histname'])
        
        if self.lot['phc_date'] not in ('0',''):
            tweet += '  - {}'.format(self.lot['phc_date'])
        elif self.lot['opa'] not in ('0',None):
            tweet += '  - {}'.format(self.lot['opa'])
            if self.lot['est'] == 'Y':
                tweet += ' (est)'
                    
        if self.lot['desigdate'] not in ('0','','pending'):
            tweet += '\nDesignated: {}'.format(self.lot['desigdate'])
            
        if self.lot['district'] != '' and self.lot['districtdate'] not in ('0','','pending'):
            tweet += '\nDistrict: {}'.format(self.lot['district'])
            tweet += '\nDistrict designated: {}'.format(self.lot['districtdate'])
            
        if self.lot['interiordate'] not in ('0','','pending'):
            tweet += '\nInterior designated: {}'.format(self.lot['interiordate'])
        
        return tweet


    def compose(self, media_id_string):
        '''
        Compose a tweet, including media ids and location info.
        :media_id_string str identifier for an image uploaded to Twitter
        '''
        self.logger.debug("media_id_string: %s", media_id_string)

        # Let missing addresses play through here, let the program leak out a bit
        status = self.write_tweet()

        return {
            "status": status,
            "lat": self.lot.get('lat', 0.),
            "long": self.lot.get('lon', 0.),
            "media_ids": [media_id_string]
        }

    def mark_as_tweeted(self, status_id):
        self.conn.execute("UPDATE lots SET tweeted = ? WHERE id = ?", (status_id, self.lot['id'],))
        self.conn.commit()
