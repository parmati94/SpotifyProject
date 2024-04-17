menu_options = {
    1: 'Create daily playlist',
    2: 'Extend weekly playlist',
    3: 'Delete all daily playlists',
    4: 'Create playlist based on another playlist',
    5: 'Extend existing playlist',
    6: 'Help menu',
    7: 'Exit program',
    8: 'Logout of Spotify account'
}
playlist_types = [1, 2]
playlist_sizes = [1, 2, 3, 4]


# Menu options for main program menu.  Returns -1 if input passed is not an integer
def print_menu_options():
    print('\nSelect menu option: \n')
    
    for key, value in menu_options.items():
        print(f"{key}. {value}")
        
    choice = input("\nInput #: ")
    print("\n")
    
    if not choice.isnumeric() or int(choice) not in menu_options:
        return -1

    return int(choice)


def playlist_type_options(choice=None):
    if choice is None:
        print('\nSelect option for playlist type: \n')
        print('1. Recommendations based on top songs')
        print('2. Recommendations based on existing playlist')   
        choice = int(input("\nInput #: "))
        print("\n")

    if choice in playlist_types:
        return choice
    else:
        print("Invalid option selected.")
        exit(0)


def playlist_size_options(choice=None):
    if choice is None:
        print('\nSelect option for number of songs to add: \n')
        print('1. 20 songs')
        print('2. 40 songs')
        print('3. 60 songs')
        print('4. 80 songs')
        choice = int(input("\nInput #: "))
        print("\n")

    if choice in playlist_sizes:
        return choice
    else:
        print("Invalid option selected.")
        exit(0)
        
def print_help_menu():
    print("HELP MENU\n")
    print("1 - Create daily playlist: ")
    print("Creates a daily playlist using recommendations based off of your top played songs in the last month.  New playlist name is defaulted to Month-Day-Year\n")
    print("2 - Extend weekly playlist: ")
    print("Extends the 'Weekly Extended Playlist' with recommendations based off of your top played songs in the last month.  Creates and adds songs to this playlist if it does not already exist.\n")
    print("3 - Delete all daily playlists: ")
    print("Deletes any daily playlists (menu option #1) that were created today.\n")
    print("4 - Create playlist based on another playlist: ")
    print("Creates a playlist using recommendations based off of another one of your existing playlists.  New playlist name can be specified.\n")
    print("5 - Extend existing playlist: ")
    print("Extends an existing playlist using either a) recommendations based off of your top played songs in the last month or b) recommendations based off of another one of your existing playlists.  You will need to specify both the source and target playlist names.\n")
    print("8 - Logout of Spotify account: ")
    print("Removes cached spotify credentials which will force a re-authentication when restarting the program.\n")


def get_new_playlist_name(playlist_name=None):
    if playlist_name is None:
        playlist_name = input("Enter name for new playlist: ")
    return playlist_name


def get_source_playlist_name(playlist_name=None):
    if playlist_name is None:
        playlist_name = input("Enter source playlist name to use for recommendations: ")
    return playlist_name

def get_target_playlist_name(target_name=None):
    if target_name is None:
        target_playlist = input("Enter existing playlist name to extend: ")
    return target_playlist
