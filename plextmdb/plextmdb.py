import logging, glob, os, requests, datetime, fuzzywuzzy.fuzz, time, sys
from functools import reduce
_mainDir = reduce(lambda x,y: os.path.dirname( x ), range( 2 ),
                  os.path.abspath( __file__ ) )
sys.path.append( _mainDir )
import pathos.multiprocessing as multiprocessing
from itertools import chain

from plextmdb import get_tmdb_api, TMDBEngine, TMDBEngineSimple, tmdb_apiKey
from plexcore import return_error_raw

def get_tv_ids_by_series_name( series_name: str, verify = True ) -> list:
    response = requests.get( 'https://api.themoviedb.org/3/search/tv',
                             params = { 'api_key' : tmdb_apiKey,
                                        'append_to_response': 'images',
                                        'include_image_language': 'en',
                                        'language': 'en',
                                        'sort_by': 'popularity.desc',
                                        'query' : '+'.join( series_name.split( ) ),
                                        'page' : 1 }, verify = verify )
    if response.status_code != 200: return [ ]
    data = response.json( )
    valid_results = list(filter(
        lambda result: 'name' in result and
        result['name'] == series_name and
        'id' in result, data[ 'results' ] ) )
    return list(map(lambda result: result[ 'id' ], valid_results ) )

def get_tv_info_for_series( tv_id: int, verify: bool = True ):
    response = requests.get( 'https://api.themoviedb.org/3/tv/%d' % tv_id,
                             params = { 'api_key' : tmdb_apiKey,
                                        'append_to_response': 'images',
                                        'language': 'en' }, verify = verify )
    if response.status_code != 200:
        print( response.content )
        return None
    return response.json( )

def get_tv_info_for_season( tv_id: int, season: int, verify: bool = True ):
    response = requests.get(
        'https://api.themoviedb.org/3/tv/%d/season/%d' % ( tv_id, season ),
        params = { 'api_key' : tmdb_apiKey,
                   'append_to_response': 'images',
                   'language': 'en' }, verify = verify )
    if response.status_code != 200:
        print( response.content )
        return None
    return response.json( )

def get_tv_imdbid_by_id( tv_id: int, verify: bool = True ) -> str:
    response = requests.get( 'https://api.themoviedb.org/3/tv/%d/external_ids' % tv_id,
                             params = { 'api_key' : tmdb_apiKey }, verify = verify )
    if response.status_code != 200:
        print( 'problem here, %s.' % response.content )
        return None
    data = response.json( )
    if 'imdb_id' not in data: return None
    return data['imdb_id']

#
## right now do not show specials
def get_episodes_series_tmdb( tv_id: int, verify: bool = True ) -> list:
    tmdb_tv_info = get_tv_info_for_series( tv_id, verify = verify )
    valid_seasons = sorted(filter(lambda seasno: seasno != 0,
                                  map(lambda season: season['season_number'],
                                      tmdb_tv_info[ 'seasons' ] ) ) )
    def _process_tmdb_epinfo( seasno: int ) -> list:
        #
        # must define 'airedSeason', 'airedEpisodeNumber', 'firstAired', 'overview', 'imageURL', 'episodeName'
        seasinfo = get_tv_info_for_season( tv_id, seasno, verify = verify )
        epelems = [ ]
        for epinfo in seasinfo[ 'episodes']:
            if len( set([ 'air_date', 'name', 'episode_number' ]) -
                    set( epinfo.keys( ) ) ) != 0:
                continue
            epelem = {
                'airedSeason' : seasno,
                'airedEpisodeNumber' : epinfo[ 'episode_number' ],
                'firstAired' : epinfo[ 'air_date' ],
                'episodeName' : epinfo[ 'name' ]
            }
            #'imageURL' : 'https://image.tmdb.org/t/p/w500%s' % epinfo['profile_path'] }
            if 'overview' in epinfo: epelem['overview'] = epinfo[ 'overview' ]
            if 'profile_path' in epinfo:
                epelem[ 'imageURL' ] = 'https://image.tmdb.org/t/p/w500%s' % epinfo['profile_path']
            epelems.append( epelem )
        return epelems
    #
    with multiprocessing.Pool( processes = multiprocessing.cpu_count( ) ) as pool:
        episodes = list( chain.from_iterable(
            map( _process_tmdb_epinfo, valid_seasons ) ) )
        return episodes

def get_movie_info( tmdb_id: int, verify = True ):
    response = requests.get(  'https://api.themoviedb.org/3/movie/%d' % tmdb_id,
                              params = { 'api_key' : tmdb_apiKey },
                              verify = verify )
    if response.status_code != 200:
        return None
    return response.json( )

def get_actor_ids_dict( actor_names, verify = True ):
    actor_name_dict = { }
    for actor_name in set(actor_names):
        actor_ids = [ ]
        params = { 'api_key' : tmdb_apiKey,
                   'query' : '+'.join( actor_name.split( ) ), }
        response = requests.get( 'https://api.themoviedb.org/3/search/person',
                                 params = params, verify = verify )
        if response.status_code != 200:
            continue
        data = response.json()
        total_pages = data['total_pages']
        actor_ids = list( map(lambda result: result['id'], data['results'] ) )
        if total_pages >= 2:
            for pageno in range(2, total_pages + 1 ):
                params =  { 'api_key' : tmdb_apiKey,
                            'query' : '+'.join( actor_name.split( ) ),
                            'page' : pageno }
            response = requests.get( 'https://api.themoviedb.org/3/search/person',
                                     params = params, verify = verify )
            if response.status_code != 200: continue
            data = response.json( )
            actor_ids += list( map(lambda result: result['id'], data['results'] ) )
        if len( set( actor_ids ) ) != 0:
            actor_name_dict[ actor_name ] = min(set( actor_ids ) )
    return actor_name_dict

def get_movies_by_actors( actor_name_dict, verify = True ):
    if len( actor_name_dict ) == 0: return [ ]
    response = requests.get( 'https://api.themoviedb.org/3/discover/movie',
                             params = { 'api_key' : tmdb_apiKey,
                                        'append_to_response': 'images',
                                        'include_image_language': 'en',
                                        'language': 'en',
                                        'page': 1,
                                        'sort_by': 'popularity.desc',
                                        'with_cast' : ','.join(map(lambda num: '%d' % num,
                                                                   actor_name_dict.values( ) ) ) },
                             verify = verify )
    if response.status_code != 200: return [ ]
    data = response.json( )
    total_pages = data['total_pages']
    results = data['results']
    if total_pages >= 2:
        for pageno in range( 2, total_pages + 1 ):
            response = requests.get( 'https://api.themoviedb.org/3/discover/movie',
                                     params = { 'api_key' : tmdb_apiKey,
                                                'append_to_response': 'images',
                                                'include_image_language': 'en',
                                                'language': 'en',
                                                'sort_by': 'popularity.desc',
                                                'with_cast' : ','.join(map(lambda num: '%d' % num,
                                                                           actor_name_dict.values( ) ) ),
                                                'page' : pageno }, verify = verify )
            if response.status_code != 200:
                continue
            data = response.json( )
            results += data[ 'results' ]
    # return results
    actualMovieData = [ ]
    moviePosterMainURL = 'https://image.tmdb.org/t/p/w500'
    movieListMainURL = 'https://api.themoviedb.org/3/discover/movie'
    for datum in results:
        if 'poster_path' not in datum or datum['poster_path'] is None:
            poster_path = None
        else:
            poster_path = moviePosterMainURL + datum['poster_path']
        if 'vote_average' not in datum:
            vote_average = 0.0
        else:
            if 'vote_count' not in datum or int( datum[ 'vote_count' ] ) <= 10:
                vote_average = 0.0
            else:
                vote_average = float( datum[ 'vote_average' ] )
        try:
            datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' ),
            row = {
                'title' : datum[ 'title' ],
                'release_date' : datetime.datetime.strptime(
                    datum['release_date'], '%Y-%m-%d' ),
                'popularity' : datum[ 'popularity' ],
                'vote_average' : vote_average,
                'overview' : datum[ 'overview' ],
                'poster_path' : poster_path,
                'isFound' : False
            }
            if 'id' in datum: row[ 'tmdb_id' ] = datum[ 'id' ]
        except Exception:
            pass
        actualMovieData.append( row )
    return actualMovieData

def get_movies_by_title( title: str, verify = True, apiKey = None ) -> list:
    if apiKey is None: apiKey = tmdb_apiKey
    response = requests.get( 'https://api.themoviedb.org/3/search/movie',
                             params = { 'api_key' : apiKey,
                                        'append_to_response': 'images',
                                        'include_image_language': 'en',
                                        'language': 'en',
                                        'sort_by': 'popularity.desc',
                                        'query' : '+'.join( title.split( ) ),
                                        'page' : 1 }, verify = verify )
    if response.status_code != 200: return [ ]
    data = response.json( )
    total_pages = data['total_pages']
    results = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 10.0,
                           data['results'] ) )
    results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    if total_pages >= 2:
        for pageno in range( 2, max( 5, total_pages + 1 ) ):
            response = requests.get( 'https://api.themoviedb.org/3/search/movie',
                                     params = { 'api_key' : apiKey,
                                                'append_to_response': 'images',
                                                'include_image_language': 'en',
                                                'language': 'en',
                                                'sort_by': 'popularity.desc',
                                                'query' : '+'.join( title.split( ) ),
                                                'page' : pageno }, verify = verify )
            if response.status_code != 200:
                continue
            data = response.json( )
            newresults = list(
                filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 10.0,
                       data['results'] ) )
            if len( newresults ) > 0:
                results += sorted( newresults, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    #return results
    actualMovieData = [ ]
    moviePosterMainURL = 'https://image.tmdb.org/t/p/w500'
    movieListMainURL = 'https://api.themoviedb.org/3/discover/movie'
    for datum in results:
        if 'poster_path' not in datum or datum['poster_path'] is None:
            poster_path = None
        else:
            poster_path = moviePosterMainURL + datum['poster_path']
        if 'vote_average' not in datum:
            vote_average = 0.0
        else:
            if 'vote_count' not in datum or int( datum[ 'vote_count' ] ) <= 10:
                vote_average = 0.0
            else:
                vote_average = float( datum[ 'vote_average' ] )
        try:
            datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' ),
            row = {
                'title' : datum[ 'title' ],
                'release_date' : datetime.datetime.strptime( datum['release_date'], '%Y-%m-%d' ),
                'popularity' : datum[ 'popularity' ],
                'vote_average' : vote_average,
                'overview' : datum[ 'overview' ],
                'poster_path' : poster_path,
                'isFound' : False
            }
            if 'id' in datum:
                row[ 'tmdb_id' ] = datum[ 'id' ]
                imdb_id = get_imdbid_from_id( row[ 'tmdb_id' ], verify = verify )
                if imdb_id is not None: row[ 'imdb_id' ] = imdb_id
        except Exception: pass
        actualMovieData.append( row )
    return actualMovieData

# Followed advice from https://www.themoviedb.org/talk/5493b2b59251416e18000826?language=en
def get_imdbid_from_id( id: int, verify = True ):
    response = requests.get( 'https://api.themoviedb.org/3/movie/%d' % id,
                             params = { 'api_key' : tmdb_apiKey }, verify = verify )
    if response.status_code != 200:
        print( 'problem here, %s.' % response.content )
        return None
    data = response.json( )
    if 'imdb_id' not in data: return None
    return data['imdb_id']

def get_movie( title: str, year = None, checkMultiple = True, getAll = False,
               verify = True ):
    movieSearchMainURL = 'https://api.themoviedb.org/3/search/movie'
    params = { 'api_key' : tmdb_apiKey,
               'append_to_response': 'images',
               'include_image_language': 'en',
               'language': 'en',
               'sort_by': 'popularity.desc',
               'query' : '+'.join( title.split( ) ),
               'page' : 1 }
    if year is not None:
        params[ 'primary_release_year' ] = int( year )
    response = requests.get( movieSearchMainURL, params = params,
                             verify = verify )
    data = response.json( )
    if 'total_pages' in data:
        total_pages = data['total_pages']
        results = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 90.0,
                         data['results'] ) )
        results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    else: return None
    if len(results) == 0:
        if checkMultiple:
            indices = range(len(title.split()))
            for idx in indices:
                split_titles = title.split()
                split_titles[idx] = split_titles[idx].upper( )
                newtitle = ' '.join( split_titles )
                val = get_movie( newtitle, year = year, checkMultiple = False )
                if val is not None:
                    return val
        return None
    if not getAll:
        first_movie = results[0]
        return 'https://www.themoviedb.org/movie/%d' % first_movie['id']
    else:
        return results

def get_movie_tmdbids( title: str, year: int = None, getAll = False, verify = True ):
    results = get_movie( title, year = year, checkMultiple = True, getAll = True,
                         verify = verify )
    if results is None: return None
    ids = list(map(lambda result: result['id'], results ) )
    if not getAll: return ids[0]
    else: return ids                   

#
## funky logic needed here...
def get_genre_movie( title: str, year: int = None, checkMultiple = True, verify = True ) -> str:
    movieSearchMainURL = 'http://api.themoviedb.org/3/search/movie'
    params = { 'api_key' : tmdb_apiKey,
               'query' : '+'.join( title.split( ) ),
               'page' : 1 }
    if year is not None:
        params[ 'primary_release_year' ] = int( year )
    response = requests.get( movieSearchMainURL, params = params,
                             verify = verify )
    data = response.json( )
    if 'total_pages' in data:
        total_pages = data['total_pages']
        results = list( filter(lambda result: fuzzywuzzy.fuzz.ratio( result['title'], title ) >= 90.0,
                               data['results'] ) )
        results = sorted( results, key = lambda result: -fuzzywuzzy.fuzz.ratio( result['title'], title ) )
    else: results = [ ]
    if len(results) == 0:
        if checkMultiple:
            indices = range(len(title.split()))
            for idx in indices:
                split_titles = title.split()
                split_titles[idx] = split_titles[idx].upper( )
                newtitle = ' '.join( split_titles )
                val = get_genre_movie( newtitle, year = year, checkMultiple = False )
                if val is not None:
                    return val
        return None
    first_movie = results[0]
    genre_ids = first_movie['genre_ids']
    for genre_id in genre_ids:
        val = TMDBEngineSimple( verify ).getGenreFromGenreId( genre_id ).lower( )
        if val in ( 'horror', 'comedy', 'animation', 'documentary', 'drama',
                    'action', 'hindi', 'horror', 'science fiction' ):
            return val
        if val == 'fantasy':
            return 'science fiction'
        if val == 'family':
            return 'drama'

def get_main_genre_movie( movie_elem: str ) -> str:
    def postprocess_genre( genre ):
        if 'sci-fi' in genre:
            return 'science fiction'
        if genre == 'adventure':
            return 'action'
        if genre == 'thriller':
            return 'action'
        if genre == 'crime':
            return 'drama'
        if genre == 'romance':
            return 'drama'
        if genre == 'factual':
            return 'documentary'
        if genre == 'war':
            return 'drama'
        if genre == 'mystery':
            return 'horror'
        return genre
    
    if len(movie_elem.find_all('genre') ) == 0:
        val = get_genre_movie( movie_elem[ 'title' ] )
        if val is None: return 'unclassified'
        return val
    classic_genres = [ 'horror', 'comedy', 'animation', 'documentary', 'drama',
                       'action', 'hindi', 'horror', 'science fiction' ]
    genres = list( map(lambda elem: elem['tag'].lower( ).strip( ), movie_elem.find_all( 'genre' ) ) )
    for genre in genres:
        if genre in classic_genres:
            return genre
    val = get_genre_movie( movie_elem[ 'title' ] )
    if val is not None: return val
    return postprocess_genre( genres[ 0 ] )
                             
def getMovieData( year: int, genre_id: str, verify = True ) -> list:
    moviePosterMainURL = 'https://image.tmdb.org/t/p/w500'
    movieListMainURL = 'https://api.themoviedb.org/3/discover/movie'
    params = { 'api_key' : tmdb_apiKey,
               'append_to_response': 'images',
               'include_image_language': 'en',
               'language': 'en',
               'page': 1,
               'primary_release_year': year,
               'sort_by': 'popularity.desc',
               'with_genres': genre_id }
    if genre_id == -1: params.pop( 'with_genres' )
    response = requests.get( movieListMainURL, params = params,
                             verify = verify )
    logging.debug('RESPONSE STATUS FOR %s = %s.' % ( str(params), str(response) ) )
    total_pages = response.json()['total_pages']
    data = list( filter(lambda datum: datum['title'] is not None and
                        datum['release_date'] is not None and
                        datum['popularity'] is not None, response.json( )['results'] ) )
    for pageno in range( 2, total_pages + 1 ):
        params['page'] = pageno
        response = requests.get( movieListMainURL, params = params, verify = verify )
        if response.status_code != 200: continue
        logging.debug('RESPONSE STATUS FOR %s = %s.' % ( str(params), str(response) ) )
        data += list( filter(lambda datum: datum['title'] is not None and
                             datum['release_date'] is not None and
                             datum['popularity'] is not None, response.json( )['results'] ) )
    actualMovieData = [ ]
    for datum in data:
        if 'poster_path' not in datum or datum['poster_path'] is None:
            poster_path = None
        else:
            poster_path = moviePosterMainURL + datum['poster_path']
        if 'vote_average' not in datum:
            vote_average = 0.0
        else:
            if 'vote_count' not in datum or int( datum[ 'vote_count' ] ) <= 10:
                vote_average = 0.0
            else:
                vote_average = float( datum[ 'vote_average' ] )
        row = {
            'title' : datum[ 'title' ],
            'release_date' : datetime.datetime.strptime(
                datum['release_date'], '%Y-%m-%d' ),
            'popularity' : datum[ 'popularity' ],
            'vote_average' : vote_average,
            'overview' : datum[ 'overview' ],
            'poster_path' : poster_path,
            'isFound' : False
        }
        if 'id' in datum: row[ 'tmdb_id' ] = datum[ 'id' ]
        actualMovieData.append( row )
    return actualMovieData
