import os
from datetime import datetime
import random

# sp = spotify_auth()

# Determines date and returns in specific format (Month-Day-Year)
def get_date():
    today = datetime.today()
    date = today.strftime("%b-%d-%Y")

    return date


# Retrieves current authenticated Spotify user
def get_current_user(sp):
    user_id = sp.me()['id']
    return user_id


# Forces re-auth for spotify by deleting .cache
def re_auth():
    if os.path.exists(".cache"):
            os.remove(".cache")
            print("Successfully removed login credentials.  You will need to re-authenticate.")
    

# Print playlist names returned from get_all_playlists
def print_all_playlist_names(sp):
    playlists = get_all_playlists(sp)
    list_num = 1
    for playlist in playlists:
        print(f"{list_num}. {playlist['name']}")
        list_num += 1
     
        
# Returns tuple with boolean and playlist ID to denote if playlist name passed already exists for user
# This may be replaced later if separating functionality
#  between getting playlist_exists & get_playlist_id makes more sense
def playlist_exists_with_id(playlist_name, sp):
    list_of_playlist_items = get_all_playlists(sp)

    for item in list_of_playlist_items:
        if item['name'] == playlist_name:
            return True, item['id']

    return False, None


# retrieves user's top tracks in the short-term, size will always = 20
def get_top_tracks(sp):
    print('Getting top tracks...')
    top_tracks = sp.current_user_top_tracks(time_range='short_term', limit=20, offset=0)
    return top_tracks


# Looks at passed list of tracks and creates track_list with only track ID's
def create_track_list(tracks):
    track_list = []

    # print(playlist_data['items'][0]['track']['id'])
    # recommended_tracks = get_recommendation_tracks(playlist_data['items'], 4)

    if 'items' in tracks:  # Used when parsing tracks derived from certain API returns
        for idx, item in enumerate(tracks['items']):
            track = item['id']
            track_list.append(track)

    else:  # Used when parsing tracks derived from playlist data
        for idx, item in enumerate(tracks):
            track = item['track']['id']
            track_list.append(track)

    return track_list


# Splits full track_list in to 2D list of lists
# num var is determined by size of 2d list (number of lists in the list - each list will always be 5 long)
# Number of lists in split_tracks can currently be either 2 (5 + 5 = 10 total seeds) or 4 (5 + 5 + 5 +5 = 20 total seeds)
# Each recommendation return limit = 20. with 5 seeds for each.
# Number of lists = 2 = 40 tracks, Number of lists = 4 = 80 returned tracks
def track_split(track_list, num):
    w, h = 5, num
    split_tracks = [[0 for x in range(w)] for y in range(h)]

    i, j = 0, 0
    q = 0

    print('Splitting top tracks...')
    while i < num:
        if j < 5:
            split_tracks[i][j] = track_list[q]
            j += 1
            q += 1
        else:
            j = 0
            i += 1

    return split_tracks


# Retrieves recommended tracks based from spotify API based on track_list seeds
# num var is determined by size of 2d list (number of lists in the list - each list will always be 5 long)
def get_recommendations(split_tracks, num, sp):
    recommendations = []
    print('Seeding recommendations...')
    for x in range(num):
        # print(f"Split tracks: {split_tracks[x]}")
        temp_rec = sp.recommendations(seed_artists=None, seed_genres=None, seed_tracks=split_tracks[x], country=None,
                                      limit=20)
        temp_rec_id = []
        for idx, item in enumerate(temp_rec['tracks']):
            track = item['id']
            temp_rec_id.append(track)

        recommendations.extend(temp_rec_id)

    random.shuffle(recommendations)
    return recommendations


# Creates playlist and populates with passed song list ('recommendations')
# Currently defaults playlist to private
def create_playlist(user, name, recommendations, sp):
    print('Creating playlist...')
    playlist = sp.user_playlist_create(user, name, public=False, collaborative=False, description="")
    playlist_id = playlist['id']
    for i in range(0, len(recommendations), 100):
        chunk = recommendations[i:i+100]
        sp.playlist_add_items(playlist_id, chunk)


def get_playlist_data(playlist_id, sp, playlist_offset=0):
    playlist_data = sp.playlist_items(playlist_id, offset=playlist_offset, limit=100)
    return playlist_data


# Returns all playlists for the current users
def get_all_playlists(sp):
    playlists = []
    offset = 0

    while True:
        batch = sp.current_user_playlists(offset=offset) # Default spotify limit is 50
        playlists.extend(batch['items'])
        offset += len(batch['items'])
        if offset >= batch['total']:
            break

    return playlists


# Takes playlist name and returns list of all playlist ID's that correspond to that name
def get_playlist_ids_with_name(name, sp):
    list_of_playlists = get_all_playlists(sp)
    playlists_with_name = []

    for playlist in list_of_playlists:
        if playlist['name'] == name:
            playlists_with_name.append(playlist['id'])

    return playlists_with_name


# Returns list of recommended tracks based on raw list of tracks
# Max # of seeds for recommendations = 5 - lists in the split_tracks are always 5 long
def get_recommendation_tracks(raw_track_list, num_lists, sp):
    track_list = create_track_list(raw_track_list)

    split_tracks = track_split(track_list, num_lists)

    recommendations = get_recommendations(split_tracks, num_lists, sp)

    return recommendations


# Makes call to API to extend existing playlist after determining playlist ID
def add_songs_to_playlist(play_id, tracks, sp):
    add_tracks = sp.playlist_add_items(playlist_id=play_id, items=tracks)
    if add_tracks:
        return True


# Checks if playlist specified exists
# If exists, retrieves recommended tracks (40) and adds to playlist
# If does not exist, creates playlist with specified name and adds recommended tracks (40)
def extend_playlist(target_playlist_name, target_playlist_id, sp, provide_options=False):  

    if provide_options:
        type_choice = playlist_type_options()
        size_choice = playlist_size_options()
    else:
        type_choice = 1 # default value - gets recommendations based on top tracks
        size_choice = 2 # default value - extends by 40 songs

    if type_choice == 2:
        print_all_playlist_names()
        source_playlist_name = get_source_playlist_name()
        playlist_exists, source_playlist_id = playlist_exists_with_id(source_playlist_name, sp)
        if playlist_exists:
            tracks = get_recommendations_from_playlist(source_playlist_name, source_playlist_id, size_choice, sp)
        else:
            print("Playlist extension failed.  Source playlist does not exist.")
            return False
    else:
        top_tracks = get_top_tracks(sp)
        tracks = get_recommendation_tracks(top_tracks, size_choice, sp)

    if tracks:
        print(f"Adding songs to playlist: {target_playlist_name}")
        success = add_songs_to_playlist(target_playlist_id, tracks, sp)
        if success:
            print(f"Songs added successfully to playlist: {target_playlist_name}")
            return True

        else:
            return False


# Deletes playlists based on each playlist ID in playlist_id list
def delete_playlists(name, playlist_ids, sp):
    count = 0

    if playlist_ids:
        for playlist_id in playlist_ids:
            sp.current_user_unfollow_playlist(playlist_id)
            count += 1
        message = f"Deleted {count} playlist(s) with name: {name}"
        print(message)
        return message
    else:
        print(f"No playlists exist with name: {name}")
        return f"No playlists exist with name: {name}"


# Retrieves recommendations based on playlist songs
def get_recommendations_from_playlist(playlist_name, playlist_id, num_lists, sp):
    playlist_data = get_playlist_data(playlist_id, sp)
    total_tracks = playlist_data['total']
    print(f"Total # of tracks: {total_tracks}")
    
    if total_tracks < 20:
        return False, f"Playlist contains only {total_tracks} tracks. At least 20 tracks are required."
    elif num_lists > total_tracks / 5:
        max_songs = (total_tracks * 4) // 20 * 20
        return False, f"Playlist has {total_tracks} songs - max number of songs in new playlist is {max_songs}."
    else:
        playlist_offset = total_tracks - (num_lists * 5)
        print(f'Playlist offset: {playlist_offset}')
        playlist_data = get_playlist_data(playlist_id, sp, playlist_offset)
        recommended_tracks = get_recommendation_tracks(playlist_data['items'], num_lists, sp)

        return True, recommended_tracks


