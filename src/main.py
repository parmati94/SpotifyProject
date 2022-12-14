import setup.config as config
from input import *
from helpers import *

date = get_date()

# Creates playlist of size 80 based off of another playlist
def create_playlist_from_playlist():
    print_all_playlist_names()
    playlist_name = get_existing_playlist_name()
    playlist_exists, playlist_id = playlist_exists_with_id(playlist_name)
    if playlist_exists:
        recommended_tracks = get_recommendations_from_playlist(playlist_name, playlist_id, 4)
        if recommended_tracks:
            playlist_name = get_new_playlist_name()
            create_playlist(get_current_user(), playlist_name, recommended_tracks)
            print(f"Playlist created: {playlist_name}")
        else:
            print(f"Playlist creation failed.  Playlist must contain at least 20 tracks.")
    else:
        print(f"Playlist creation failed.  Playlist must already exist.")


def weekly_extended_playlist():
    playlist_exists, playlist_id = playlist_exists_with_id('Weekly Extended Playlist')
    if playlist_exists:
        extend_playlist('Weekly Extended Playlist', playlist_id, provide_options=False)
    else:
        print("Weekly Extended Playlist does not exist.  Creating playlist and adding songs...")
        create_daily_recommendation_playlist('Weekly Extended Playlist', 2)


def extend_existing_playlist():
    print_all_playlist_names()
    playlist_name = get_existing_playlist_name()
    playlist_exists, playlist_id = playlist_exists_with_id(playlist_name)
    if playlist_exists:
       extend_playlist(playlist_name, playlist_id, provide_options=True) 
    else:
        print("Playlist does not exist.  Please enter a valid playlist name.")

# Creates standard recommendation playlist based on a user's top tracks
def create_daily_recommendation_playlist(name, num_lists):
    top_tracks = get_top_tracks()

    recommendations = get_recommendation_tracks(top_tracks, num_lists)

    user = get_current_user()
    playlist_name = name

    create_playlist(user, playlist_name, recommendations)

    print(f"Playlist created with name: {playlist_name}")

# Determines all playlists that exist with current date as name and passes to delete function
def delete_all_daily_playlists():
    playlist_ids = get_playlist_ids_with_name(date)
    delete_playlists(date, playlist_ids)


# This is a main function...
def main():
    choice = 0

    while choice != 6:

        choice = menu_options()

        if choice == 1:
            create_daily_recommendation_playlist(date, 4)
        elif choice == 2:
            weekly_extended_playlist()
        elif choice == 3:
            delete_all_daily_playlists()
        elif choice == 4:
            create_playlist_from_playlist()
        elif choice == 5:
            extend_existing_playlist()
        elif choice == 6:
            exit(0)
        elif choice == 7:
            re_auth()           


if __name__ == "__main__":
    main()
