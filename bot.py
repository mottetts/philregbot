# -*- coding: utf-8 -*-

import argparse
import logging
import twitter_bot_utils as tbu
# from . import __version__ as version
from everylot import EveryLot


def main(): 
    
    parser = argparse.ArgumentParser(description='every lot twitter bot')
    parser.add_argument('screen_name', metavar='SCREEN_NAME', type=str, help='Twitter screen name (without @)')
    parser.add_argument('database', metavar='DATABASE', type=str, help='path to SQLite lots database')
    parser.add_argument('--id', type=str, default=None, help='tweet the entry in the lots table with this id')
    parser.add_argument('-s', '--search-format', type=str, default=None, metavar='STRING',
                        help='Python format string use for searching Google')
    parser.add_argument('-p', '--print-format', type=str, default=None, metavar='STRING',
                        help='Python format string use for poster to Twitter')
    tbu.args.add_default_args(parser, version='0.3.1', include=('config', 'dry-run', 'verbose', 'quiet'))

    args = parser.parse_args()
    api = tbu.api.API(args)

    logger = logging.getLogger(args.screen_name)
    logger.debug('everylot starting with %s, %s', args.screen_name, args.database)

    el = EveryLot(args.database,
                  logger=logger,
                  print_format=args.print_format,
                  search_format=args.search_format,
                  id_=args.id)

    if not el.lot:
        logger.error('No lot found')
        return

    logger.debug('%s addresss: %s zip: %s', el.lot['id'], el.lot.get('address'), el.lot.get('zip'))
    logger.debug('db location %s,%s', el.lot['lat'], el.lot['lon'])

    # Get the streetview image and upload it
    # ("sv.jpg" is a dummy value, since filename is a required parameter).
    image = el.get_streetview_image(api.config['streetview'])
    media = api.media_upload('sv.jpg', file=image)

    # compose an update with all the good parameters
    # including the media string.
    update = el.compose(media.media_id_string)
    logger.info('tweet length: {} chars'.format(len(update['status'])))
    logger.info(update['status'])

    if not args.dry_run:
        logger.debug("posting")
        status = api.update_status(**update)
        try:
            el.mark_as_tweeted(status.id)
        except AttributeError:
            el.mark_as_tweeted('1')

if __name__ == '__main__':
    main()
