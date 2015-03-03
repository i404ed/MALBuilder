from app import db
from models import Anime, AnimeToGenre, UserToAnime, UserToTag
from datetime import datetime
from sqlalchemy import or_
import json


AA_FILTERS = {
    'malIdStart': lambda x: Anime.malId >= x,
    'malIdEnd': lambda x: Anime.malId <= x,
    'type': lambda x: or_(*[Anime.type == xi for xi in x]),
    'status': lambda x: or_(*[Anime.status == xi for xi in x]),
    'title': lambda x: Anime.title == x,
    'startDateStart': lambda x: Anime.startDate >= x,
    'startDateEnd': lambda x: Anime.startDate <= x,
    'endDateStart': lambda x: Anime.endDate >= x,
    'endDateEnd': lambda x: Anime.endDate <= x,
    'scoreStart': lambda x: Anime.score >= x,
    'scoreEnd': lambda x: Anime.score <= x,
    'membersStart': lambda x: Anime.members >= x,
    'membersEnd': lambda x: Anime.members <= x
}


def search_anime(filters, fields):
    """Search anime in anime database matching filters and return given fields"""
    my_fields = []
    for f in fields:
        if hasattr(Anime, f):
            my_fields.append(getattr(Anime, f))

    my_filters = []
    for f in AA_FILTERS:
        if filters.get(f):
            my_filters.append(AA_FILTERS[f](filters[f]))

    return db.session.query(*my_fields).filter(*my_filters).all()


def parse_mal_entry(user_id, anime):
    """Parses an MAL anime entry into DB user format"""
    anime_id = anime.find('series_animedb_id').text
    utoa = UserToAnime(user_id, anime_id)

    utoa.myId = anime.find('my_id').text
    utoa.watchedEps = anime.find('my_watched_episodes').text
    utoa.startDate = anime.find('my_start_date').text
    utoa.endDate = anime.find('my_finish_date').text
    utoa.score = anime.find('my_score').text
    utoa.status = anime.find('my_status').text
    utoa.rewatching = anime.find('my_rewatching').text is 1
    utoa.rewatchEps = anime.find('my_rewatching_ep').text
    utoa.lastUpdate = anime.find('my_last_updated').text

    tags = []
    for tag in anime.find('my_tags'):
        utot = UserToTag(user_id, anime_id, tag)
        tags.append(utot)

    return utoa, tags


def parse_mal_data(tree):
    """Parses all MAL entries into DB from the given XML"""
    user_id = tree.find('myinfo').find('user_id').text
    print(user_id)
    for anime in tree.findall('anime'):
        curr, tags = parse_mal_entry(user_id, anime)
        print(curr.animeId)


def parse_aa_entry(anime):
    """Parses an AA anime entry into DB anime format"""
    anime = anime['i']

    info = anime['11'][0]
    mal_id = info['a']
    curr = Anime(mal_id)
    curr.type = info.get('b')
    curr.status = info.get('c')
    curr.engTitle = info.get('d')
    curr.japTitle = info.get('e')
    curr.imgLink = info.get('f')

    info = anime['12'][0]
    curr.startDate = datetime.utcfromtimestamp(info.get('a', 0))
    curr.endDate = datetime.utcfromtimestamp(info.get('b', 0))
    curr.description = info.get('e')

    genres = []
    for genre in anime['14']:
        atog = AnimeToGenre(mal_id, genre['a'])
        genres.append(atog)

    info = anime['15'][0]
    curr.score = info.get('a')
    curr.favorites = info.get('b')
    curr.members = info.get('c')
    curr.scoreCount = info.get('d')

    info = anime['2'][0]
    curr.title = info['a']

    return curr, genres


def parse_aa_data(filepath):
    """Parses all AA entries into DB from the given file"""
    with open(filepath, 'r') as file:
        for line in file:
            for anime in json.loads(line)['objects']:
                curr, genres = parse_aa_entry(anime)
                # print('{}\'s genres: {}'.format(curr.title, ', '.join([AA_GENRES[x.genreId] for x in genres])))

                db.session.add(curr)
                for genre in genres:
                    db.session.add(genre)

    db.session.commit()