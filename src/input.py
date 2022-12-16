playlist_types = [1, 2]
playlist_sizes = [1, 2, 3, 4]


# Menu options for main program menu.  Returns -1 if input passed is not an integer
def menu_options():
    print('\nSelect menu option: \n')
    print('1. Create playlist based on recommendations')
    print('2. Extend weekly playlist')
    print('3. Delete all daily playlists')
    print('4. Create playlist based on another playlist')
    print('5. Extend existing playlist')
    print('6. Exit program')
    print('7. Logout of Spotify account')

    choice = input("\nInput #: ")
    print("\n")
    
    if not choice.isnumeric():
        return -1

    return int(choice)


def playlist_type_options():
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


def playlist_size_options():
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


def get_new_playlist_name():
    playlist_name = input("Enter name for new playlist: ")
    return playlist_name


def get_source_playlist_name():
    playlist_name = input("Enter source playlist name to use for recommendations: ")
    return playlist_name

def get_target_playlist_name():
    target_playlist = input("Enter existing playlist name to extend: ")
    return target_playlist
