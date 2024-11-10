#!/usr/bin/env python3

import os
import sys
import datetime
import argparse
import requests
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple
from urllib.parse import urlparse

class PostInitializer:
    def __init__(self):
        # Core variables - use current working directory as base
        self.base_path = os.getcwd()
        self.posts_path = os.path.join(self.base_path, "_posts")
        self.img_path = os.path.join(self.base_path, "assets", "img")
        
        # Create necessary directories if they don't exist
        os.makedirs(self.posts_path, exist_ok=True)
        os.makedirs(self.img_path, exist_ok=True)
        
        # Settings
        self.blog_url = "https://tbrsvn.github.io/"
        self.assets_url = "/assets/img/"
        
        # OMDB API settings
        self.omdb_api_key = input("OMDB API Key: ")
        self.omdb_base_url = "http://www.omdbapi.com/"
        
        # GitHub settings
        self.repo_url = "https://github.com/tbrsvn/tbrsvn.github.io"

    def generate_star_rating(self, rating: float) -> str:
        """Generate star rating string with the last star being a glowing/sparkle star."""
        if not 1 <= rating <= 10:
            raise ValueError("Rating must be between 1 and 10")
        
        # Handle whole number and decimal part separately
        whole_stars = int(rating)
        has_half = rating % 1 == 0.5
        
        if has_half:
            stars = "⭐" * whole_stars + "💫"  # Use whole_stars (not -1) for half ratings
        else:
            stars = "⭐" * (whole_stars - 1) + "🌟"  # Keep same for whole numbers
        
        total = "⭐" * 9 + "🌟"  # Total stays the same
        return f"{stars}/{total}<br>{rating}/10"

    def read_review_content(self) -> Optional[str]:
        """Read review content from review.md file."""
        review_path = os.path.join(self.base_path, "review.md")
        try:
            with open(review_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"✖ Error reading review.md: {str(e)}")
            return None

    def download_image(self, image_url: str, movie_name: str) -> Optional[str]:
        """Download image and return local path."""
        if not image_url or image_url == "N/A":
            return None

        try:
            # Get file extension from URL
            parsed_url = urlparse(image_url)
            ext = os.path.splitext(parsed_url.path)[1]
            if not ext:
                ext = '.jpg'  # Default to jpg if no extension found

            # Create filename
            clean_name = ''.join(c for c in movie_name.lower() if c.isalnum() or c == '-')
            local_filename = f"{clean_name}-poster{ext}"
            local_path = os.path.join(self.img_path, local_filename)

            # Download image
            response = requests.get(image_url)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                f.write(response.content)

            return f"{self.assets_url}{local_filename}"

        except Exception as e:
            print(f"✖ Error downloading image: {str(e)}")
            return None
    
    def process_title(self, input_title: str) -> Tuple[str, str]:
        """
        Process the input title to return both the formatted title and clean movie name.
        Returns tuple of (formatted_title, movie_name)
        """
        movie_name = input_title.replace("Toma's Review Of:", "").strip()
        formatted_title = f"Toma's Review Of: {movie_name}"
        return (formatted_title, movie_name)
        
    def fetch_movie_data(self, title: str) -> Optional[Dict]:
        """Fetch movie data from OMDB API."""
        try:
            params = {
                'apikey': self.omdb_api_key,
                't': title,
                'plot': 'full'
            }
            response = requests.get(self.omdb_base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('Response') == 'True':
                return data
            return None
            
        except requests.RequestException as e:
            print(f"✖ Error fetching movie data: {str(e)}")
            return None
    
    def create_post_filename(self, movie_name: str) -> str:
        """Create a filename from the movie name."""
        current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        clean_name = movie_name.lower().replace(' ', '-')
        clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '-')
        return f"{current_date}-{clean_name}.md"

    def get_media_type_tag(self, movie_data: Dict) -> str:
        """Determine if content is movie or TV series."""
        media_type = movie_data.get('Type', '').lower()
        if media_type == 'series':
            return 'TV'
        return 'Movie'

    def git_push_changes(self, movie_name: str) -> bool:
        """Push changes to GitHub repository."""
        try:
            # Git commands
            commands = [
                ['git', 'add', '_posts/*', 'assets/img/*'],
                ['git', 'commit', '-m', f'Added review for {movie_name}'],
                ['git', 'push', 'origin', 'main']
            ]
            
            print("→ Pushing changes to GitHub...")
            
            # Execute git commands
            for cmd in commands:
                result = subprocess.run(cmd, 
                                     capture_output=True, 
                                     text=True)
                if result.returncode != 0:
                    print(f"✖ Git command failed: {' '.join(cmd)}")
                    print(f"Error: {result.stderr}")
                    return False
            
            print("✔ Successfully pushed changes to GitHub")
            return True
            
        except Exception as e:
            print(f"✖ Error pushing to GitHub: {str(e)}")
            return False

    def generate_post_content(self, input_title: str, rating: int) -> str:
        """Generate the complete post content including frontmatter and review."""
        # First get the frontmatter
        formatted_title, movie_name = self.process_title(input_title)
        movie_data = self.fetch_movie_data(movie_name)
        
        # Get the year if available
        year = ""
        if movie_data and 'Year' in movie_data:
            year = f" ({movie_data['Year']})"
        
        # Set default values
        description = ""
        image = ""
        optimized_image = ""
        category = "movie-review"
        tags = ["Review"]
        
        # Update values if movie data is available
        if movie_data:
            description = movie_data.get('Plot', '')
            poster_url = movie_data.get('Poster', '')
            if poster_url and poster_url != "N/A":
                local_image_path = self.download_image(poster_url, movie_name)
                if local_image_path:
                    image = local_image_path
                    optimized_image = local_image_path
            category = movie_data.get('Genre', 'movie-review').split(',')[0].strip()
            media_type = self.get_media_type_tag(movie_data)
            tags.append(media_type)
        
        # Format tags
        tags_formatted = '\n  - '.join(tags)
        
        # Create frontmatter
        frontmatter = [
            "---",
            f"date: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            "layout: post",
            f'title: "Toma\'s Review Of: {movie_name}{year}"',
            "subtitle:",
            f'description: "{description}"',
            f'image: "{image}"',
            f'optimized_image: "{optimized_image}"',
            f'category: "{category}"',
            f'tags:\n  - {tags_formatted}',
            'author: "tomab"',
            "paginate: true",
            "---\n"
        ]
        
        # Get review content
        review_content = self.read_review_content()
        if not review_content:
            review_content = "# Review content coming soon..."
        
        # Generate star rating
        star_rating = self.generate_star_rating(rating)
        
        # Combine everything with extra newline
        return '\n'.join(frontmatter) + "\n" + review_content + f'\n\n<h4 style="text-align:center;"> {star_rating}</h4>'

    def create_post(self, input_title: str, rating: int) -> bool:
        """Create a new blog post file and push to GitHub."""
        _, movie_name = self.process_title(input_title)
        filename = self.create_post_filename(movie_name)
        filepath = os.path.join(self.posts_path, filename)
        
        if os.path.exists(filepath):
            print(f"! Warning: File {filename} already exists.")
            return False
        
        try:
            # Create the post
            content = self.generate_post_content(input_title, rating)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✔ Successfully created post: {filename}")
            print(f"  Title in post: {self.process_title(input_title)[0]}")
            
            # Push to GitHub
            if self.git_push_changes(movie_name):
                print("✔ All changes have been pushed to GitHub")
            else:
                print("! Warning: Post was created but GitHub push failed")
            
            return True
            
        except Exception as e:
            print(f"✖ Error creating post: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Initialize a new blog post with movie information from OMDB.',
        epilog='Example: %(prog)s -c "The Matrix" -r 8.5'
    )
    parser.add_argument('-c', '--create', metavar='TITLE', 
                       help='create a new post with the movie title')
    parser.add_argument('-r', '--rating', type=float,
                       help='rating from 1 to 10 (can use .5 increments)', required=True)
    
    args = parser.parse_args()
    
    if args.create:
        # Validate rating
        if args.rating % 0.5 != 0 or args.rating < 1 or args.rating > 10:
            print("Rating must be between 1 and 10 and use .5 increments")
            return
        initializer = PostInitializer()
        initializer.create_post(args.create, args.rating)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
