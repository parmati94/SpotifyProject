from .config import *
from .input import *
from .helpers import *

# Import issues? Read https://stackoverflow.com/questions/74624111/application-runs-with-uvicorn-but-cant-find-module-no-module-named-app

date = get_date()


# Driver function for menu option #1
# Creates standard recommendation playlist based on a user's top tracks
def create_daily_recommendation_playlist(name, num_lists):
    top_tracks = get_top_tracks() 

    recommendations = get_recommendation_tracks(top_tracks, num_lists)

    user = get_current_user()
    playlist_name = name

    create_playlist(user, playlist_name, recommendations)

    print(f"Playlist created with name: {playlist_name}")
    
    return f'Daily playlist created with name: {playlist_name}'
    
    
# Driver function for menu option #2
# Creates or extends Weekly Extended Playlist
def weekly_extended_playlist():
    playlist_exists, playlist_id = playlist_exists_with_id('Weekly Extended Playlist')
    if playlist_exists:
        extend_playlist('Weekly Extended Playlist', playlist_id, provide_options=False)
    else:
        print("Weekly Extended Playlist does not exist.  Creating playlist and adding songs...")
        create_daily_recommendation_playlist('Weekly Extended Playlist', 2)
        
        
# Driver function for menu option #3
# Determines all playlists that exist with current date as name and passes to delete function
def delete_all_daily_playlists():
    playlist_ids = get_playlist_ids_with_name(date)
    message = delete_playlists(date, playlist_ids)
    return message
    

# Driver function for menu option #4
# Creates playlist of size 80 based off of another playlist
def create_playlist_from_playlist(source_playlist_name=None, target_playlist_name=None):
    print_all_playlist_names()
    source_playlist_name = get_source_playlist_name(source_playlist_name)
    playlist_exists, playlist_id = playlist_exists_with_id(source_playlist_name)
    if playlist_exists:
        recommended_tracks = get_recommendations_from_playlist(source_playlist_name, playlist_id, 4)
        if recommended_tracks:
            target_playlist_name = get_new_playlist_name(target_playlist_name)
            create_playlist(get_current_user(), target_playlist_name, recommended_tracks)
            print(f"Playlist created: {target_playlist_name}")
        elif not recommended_tracks:
            print(f"Playlist creation failed.  Playlist must contain at least 20 tracks.")
    else:
        print(f"Playlist creation failed.  Source playlist must already exist.")
        

# Driver function for menu option #5
# Extends playlist that already exists with recommended songs
def extend_existing_playlist(target_playlist_name=None):
    print_all_playlist_names()
    target_playlist_name = get_target_playlist_name()
    playlist_exists, playlist_id = playlist_exists_with_id(target_playlist_name)
    if playlist_exists:
       extend_playlist(target_playlist_name, playlist_id, provide_options=True) 
    else:
        print("Playlist does not exist.  Please enter a valid playlist name.")
        
def help_menu():
    print_help_menu()

# This is a main function...
def main():

    sp = spotify_auth()
    sp.current_user() # Call must be made on 'sp' return object to force authorization prior to selecting menu options
    
    choice = 0

    while choice != 7:

        choice = print_menu_options()
        
        if choice == -1:
            print("Invalid input provided.  Input must be an integer value included on the menu.")
        elif choice == 1:
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
            help_menu()
        elif choice == 7:
            exit(0)
        elif choice == 8:
            re_auth()
            exit(0)      


if __name__ == "__main__":
    main()
