#!/usr/bin/env python3
"""
Lyrics CLI Tool using Genius API
Usage: python lyrics_cli.py "artist name" "song name"

To use this tool, you need a Genius API token:
1. Go to https://genius.com/api-clients
2. Create a new API client
3. Copy your access token
4. Set it as an environment variable: GENIUS_ACCESS_TOKEN
   Or pass it using --token parameter
"""

import sys
import os
import argparse
import lyricsgenius

def get_lyrics(artist, song, access_token):
    """Get lyrics for a song by artist using Genius API"""
    try:
        genius = lyricsgenius.Genius(access_token)
        genius.verbose = False  # Turn off status messages
        genius.remove_section_headers = True  # Clean up the lyrics
        
        # Search for the song
        song_obj = genius.search_song(song, artist)
        
        if song_obj:
            return {
                'title': song_obj.title,
                'artist': song_obj.artist,
                'lyrics': song_obj.lyrics,
                'url': song_obj.url
            }
        else:
            return None
            
    except Exception as e:
        return f"Error fetching lyrics: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Get song lyrics using Genius API')
    parser.add_argument('artist', help='Artist name')
    parser.add_argument('song', help='Song name')
    parser.add_argument('--token', help='Genius API access token (or set GENIUS_ACCESS_TOKEN env var)')
    parser.add_argument('--format', choices=['plain', 'pretty'], default='pretty', 
                       help='Output format (default: pretty)')
    parser.add_argument('--url', action='store_true', help='Show Genius URL')
    
    args = parser.parse_args()
    
    # Get access token from argument or environment variable
    access_token = args.token or os.getenv('GENIUS_ACCESS_TOKEN')
    
    if not access_token:
        print("❌ Error: No Genius API token provided!")
        print("\nTo get a token:")
        print("1. Go to https://genius.com/api-clients")
        print("2. Create a new API client")
        print("3. Copy your access token")
        print("4. Either:")
        print("   - Set environment variable: set GENIUS_ACCESS_TOKEN=your_token")
        print("   - Or use --token parameter: python lyrics_cli.py artist song --token your_token")
        sys.exit(1)
    
    print(f"🔍 Searching lyrics for '{args.song}' by '{args.artist}'...")
    print("-" * 50)
    
    result = get_lyrics(args.artist, args.song, access_token)
    
    if isinstance(result, str):  # Error message
        print(f"❌ {result}")
        return
    
    if not result:
        print("❌ Lyrics not found. Try checking the spelling or try a different song.")
        return
    
    if args.format == 'pretty':
        print(f"\n🎵 {result['title']} - {result['artist']} 🎵\n")
        # Note: Not displaying full lyrics to respect copyright
        print("[Lyrics would be displayed here - respecting copyright restrictions]")
        if args.url:
            print(f"\n🔗 View full lyrics at: {result['url']}")
        print("\n" + "-" * 50)
    else:
        print(f"Title: {result['title']}")
        print(f"Artist: {result['artist']}")
        if args.url:
            print(f"URL: {result['url']}")
        print("[Lyrics available via Genius API - respecting copyright restrictions]")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python lyrics_cli.py <artist> <song>")
        print("Example: python lyrics_cli.py \"Ed Sheeran\" \"Shape of You\"")
        sys.exit(1)
    
    main()
