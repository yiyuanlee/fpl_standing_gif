# FPL Standings Progression Visualizer

An elegant Python tool to visualize the standing/lead changes of the top 3 players in a Fantasy Premier League (FPL) mini-league. It fetches live data from the FPL API and renders a buttery-smooth, 24fps animated video (or loopable GIF) showing their cumulative points progression gameweek by gameweek.

## Features

- **Live FPL API Integration**: Dynamically fetches the current classic mini-league standings and players' week-by-week historical points.
- **Smooth Interpolation**: Interpolates 8 sub-frames between each gameweek to produce a 24fps fluid rendering.
- **Neon Dark Theme**: Sleek background, grid lines, glowing lines for players, and a monospace running scoreboard that displays real-time standings.
- **Mac/iOS Playback Compatible**: Output video uses H.264 video codec and `yuv420p` color space to play natively in QuickTime and Safari.

## Showcase

The visualizer generates a smooth MP4 video like this:

- **Video Path**: `fpl_standings_progression.mp4`
- **GIF Path**: `fpl_standings_progression.gif`

## Installation

1. Clone this repository (or copy the files).
2. Set up a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Generate MP4 Video (Recommended)
Run the video generator script. This will download a static `ffmpeg` build inside the environment and compile a 24fps video:
```bash
python generate_video.py
```

### Generate GIF
If you want to compile a loopable GIF instead:
```bash
python generate_gif.py
```

## Customization

You can change the target mini-league ID in the scripts. In both `generate_video.py` and `generate_gif.py`, update the `league_url`:
```python
league_url = "https://fantasy.premierleague.com/api/leagues-classic/<YOUR_LEAGUE_ID>/standings/"
```
You can also adjust the colors, animation speeds, and DPI resolution settings inside the scripts.
