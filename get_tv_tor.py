#!/usr/bin/env python2

import requests, fuzzywuzzy, lxml.html, re, codecs
from requests.compat import urljoin
from optparse import OptionParser
from plextvdb import plextvdb

def get_tv_torrent_tpb( name, maxnum = 10, doAny = False, raiseError = False,
                        filename = None ):
    assert( maxnum >= 5 )
    its, status = plextvdb.get_tv_torrent_tpb( name, maxnum = maxnum, doAny = doAny )
    if status != 'SUCCESS':
        if raiseError:
            raise ValueError('ERROR, COULD NOT FIND %s.' % name)
        print 'ERROR, COULD NOT FIND %s.' % name
        return
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        bs = codecs.encode( 'Choose TV episode or series:\n%s\n' %
                            '\n'.join(map(lambda idx: '%d: %s (%d SE, %d LE)' % ( idx, sortdict[ idx ][ 'title' ],
                                                                                  sortdict[ idx ][ 'seeders' ],
                                                                                  sortdict[ idx ][ 'leechers' ]),
                                          sorted( sortdict ) ) ), 'utf-8' )
        iidx = raw_input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the TV files. Exiting...')
                return
            magnet_link = sortdict[ iidx ][ 'link' ]
            actmov = sortdict[ iidx ][ 'title' ]
        except Exception:
            print('Error, did not give a valid integer value. Exiting...')
            return
    else:
        actmov = max( items )[ 'title' ]
        magnet_link = max( items )[ 'link' ]

    print('Chosen TV show: %s' % actmov )
    if filename is None:
        print('magnet link: %s' % magnet_link )
    else:
        with open(filename, 'w') as openfile:
            openfile.write('%s\n' % magnet_link )

def get_tv_torrent_torrentz( name, maxnum = 10, filename = None ):
    assert( maxnum >= 5 )
    its, status = plextvdb.get_tv_torrent_torrentz( name, maxnum = maxnum )
    if status != 'SUCCESS':
        print 'ERROR, COULD NOT FIND %s.' % name
        return
    items = [ { 'title' : item[0], 'seeders' : item[1], 'leechers' : item[2], 'link' : item[3] } for
              item in its ]
    if len( items ) != 1:
        sortdict = { idx + 1 : item for ( idx, item ) in enumerate(items) }
        bs = codecs.encode( 'Choose TV episode or series:\n%s\n' %
                            '\n'.join(map(lambda idx: '%d: %s (%d SE, %d LE)' % ( idx, sortdict[ idx ][ 'title' ],
                                                                                  sortdict[ idx ][ 'seeders' ],
                                                                                  sortdict[ idx ][ 'leechers' ]),
                                          sorted( sortdict ) ) ), 'utf-8' )
        iidx = raw_input( bs )
        try:
            iidx = int( iidx.strip( ) )
            if iidx not in sortdict:
                print('Error, need to choose one of the TV files. Exiting...')
                return
            magnet_link = sortdict[ iidx ][ 'link' ]
            actmov = sortdict[ iidx ][ 'title' ]
        except Exception:
            print('Error, did not give a valid integer value. Exiting...')
            return
    else:
        actmov = max( items )[ 'title' ]
        magnet_link = max( items )[ 'link' ]

    print('Chosen TV show: %s' % actmov )
    if filename is None:
        print('magnet link: %s' % magnet_link )
    else:
        with open(filename, 'w') as openfile:
            openfile.write('%s\n' % magnet_link )

if __name__=='__main__':
    parser = OptionParser( )
    parser.add_option('--name', dest='name', type=str, action='store',
                      help = 'Name of the movie file to get.')
    parser.add_option('--maxnum', dest='maxnum', type=int, action='store', default = 10,
                      help = 'Maximum number of torrents to look through. Default is 10.')
    parser.add_option('--any', dest='do_any', action='store_true', default = False,
                      help = 'If chosen, make no filter on movie format.')
    parser.add_option('--filename', dest='filename', action='store', type=str,
                      help = 'If defined, put option into filename.')
    opts, args = parser.parse_args( )
    assert( opts.name is not None )
    try:
        get_tv_torrent_tpb( opts.name, doAny = opts.do_any, maxnum = opts.maxnum, raiseError = True, filename = opts.filename )
    except ValueError:
        get_tv_torrent_torrentz( opts.name, maxnum = opts.maxnum,
                                 filename = opts.filename )
