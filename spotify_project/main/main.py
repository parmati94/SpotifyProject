from .operations import *

# Import issues? Read https://stackoverflow.com/questions/74624111/application-runs-with-uvicorn-but-cant-find-module-no-module-named-app

# Driver function for menu option #1
# Creates standard recommendation playlist based on a user's top tracks
def create_recommendation_playlist(name, num_lists, sp):
    top_tracks = get_top_tracks(sp) 

    recommendations = get_recommendation_tracks(top_tracks, num_lists, sp)

    user = get_current_user(sp)
    playlist_name = name

    create_playlist(user, playlist_name, recommendations, sp)

    print(f"Playlist created with name: {playlist_name}")
    
    return f'Daily playlist created with name: {playlist_name}'
    
    
# Driver function for menu option #2
# Creates or extends Weekly Extended Playlist
def weekly_extended_playlist(sp):
    playlist_exists, playlist_id = playlist_exists_with_id('Weekly Extended Playlist', sp)
    if playlist_exists:
        success = extend_playlist('Weekly Extended Playlist', playlist_id, sp)
        if success:
            return f'Weekly playlist has been extended.'
        else:
            return f'Error: Failed to extend the weekly playlist.'
    else:
        print("Weekly Extended Playlist does not exist.  Creating playlist and adding songs...")
        create_recommendation_playlist('Weekly Extended Playlist', 2, sp)
        return f'Daily playlist created with name: Weekly Extended Playlist'
        
        
# Driver function for menu option #3
# Determines all playlists that exist with current date as name and passes to delete function
def delete_all_daily_playlists(sp):
    playlist_ids = get_playlist_ids_with_name(get_date(), sp)
    message = delete_playlists(get_date(), playlist_ids, sp)
    return message
    

# Driver function for menu option #4
# Creates playlist of size 80 based off of another playlist
def create_playlist_from_playlist(source_playlist_name, target_playlist_name, num_songs, sp):
    playlist_exists, playlist_id = playlist_exists_with_id(source_playlist_name, sp)
    if playlist_exists:
        num_lists = num_songs // 20
        success, result = get_recommendations_from_playlist(source_playlist_name, playlist_id, num_lists, sp)
        if success:
            create_playlist(get_current_user(sp), target_playlist_name, result, sp)
            print(f"Playlist created: {target_playlist_name}")
            return f"Playlist created: {target_playlist_name}"
        else:
            print(result)
            return result
    else:
        print(f"Playlist creation failed.  Source playlist must already exist.")
        return f"Playlist creation failed.  Source playlist must already exist."