# Every Historic Lot PHL

A Twitter bot that posts images of historic properties and sites in Philadelphia with accompanying history from the Philadelphia Register of Historic Places. Based on the [every lot bot](https://github.com/fitnr/everylotbot) library.

## How it works

The data for the table is taken from the records of the Philadelphia Historical Commission and the Office of Property Assessment's official tax records. The bot follows the standard every lot method of pulling images from Google Streetview and posting them to Twitter. All tweets should include, at minimum, an address and a designation date for when the historic asset was added to the PRHP. Depending on what's in the records, the text of the tweet may also include the following fields:

- a historic name associated with the asset
- the year the historic asset originated. If not present in PHC's records, the year from OPA's records is used. In almost all cases, the OPA year is an estimate, indicated by the presence of (est.)
- if the asset is part of a historic district, the name of the district and date the district was designated

The table is updated regularly to match the PRHP, and is currently up to date as of 10 July 2021.
