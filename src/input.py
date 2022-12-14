# Menu options for main program menu
def menu_options():
    print('\nSelect menu option: \n')
    print('1. Create playlist based on recommendations')
    print('2. Extend weekly playlist')
    print('3. Delete all daily playlists')
    print('4. Create playlist based on another playlist')
    print('5. Extend existing playlist')
    print('6. Exit program')
    print('7. Logout of Spotify account')

    choice = int(input("\nInput #: "))
    print("\n")

    return choice


def playlist_type_options():
    print('\nSelect option for playlist type: \n')
    print('1. Recommendations based on top songs')
    print('2. Recommendations based on existing playlist')

    choice = int(input("\nInput #: "))
    print("\n")

    if choice == 1 or choice == 2:
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

    if choice == 1 or choice == 2 or choice == 3 or choice == 4:
        return choice
    else:
        print("Invalid option selected.")
        exit(0)

# Currently not in use and needs to be updated
def get_new_playlist_name():
    playlist_name = input("Enter name for new playlist: ")
    return playlist_name

def get_existing_playlist_name():
    playlist_name = input("Enter existing playlist name to extend: ")
    return playlist_name
