import os
import sys
import io
import time
import argparse
import requests
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import imageio_ffmpeg
import numpy as np
import colorsys

# Setup headers to mimic browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Tell matplotlib where ffmpeg is
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()

# Ensure standard output/error use UTF-8 on Windows to prevent UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Neon color palette
NEON_PALETTE = ['#00f5d4', '#ff007f', '#fee440', '#00bbf9', '#9b5de5', '#f15bb5', '#ff9f1c', '#06d6a0', '#ff5d73', '#72efdd']

def hsl_to_hex(h, s, l):
    """Convert HSL color values to hex string."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

def get_colors(num_players):
    """Retrieve or dynamically generate unique neon colors."""
    if num_players <= len(NEON_PALETTE):
        return NEON_PALETTE[:num_players]
    colors = list(NEON_PALETTE)
    while len(colors) < num_players:
        hue = (len(colors) * 137.5) % 360  # Use golden angle for even distribution
        colors.append(hsl_to_hex(hue, 1.0, 0.6))
    return colors

def requests_retry_get(url, headers, retries=4, backoff_factor=1.5):
    """Fetch URL using a retry strategy with exponential backoff."""
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if i == retries - 1:
                raise e
            time.sleep(backoff_factor * (i + 1))

def fetch_data(league_id, top_n):
    """Fetch league standings and individual historical gameweek results."""
    print(f"Fetching league standings for league ID {league_id}...")
    league_url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/"
    
    try:
        response = requests_retry_get(league_url, headers=HEADERS)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Error: League ID {league_id} not found. Please make sure the ID is correct.", file=sys.stderr)
        elif e.response.status_code == 403:
            print(f"Error: Access to league ID {league_id} is forbidden. This might be a private league.", file=sys.stderr)
        else:
            print(f"HTTP Error fetching standings: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Network error fetching standings: {e}", file=sys.stderr)
        sys.exit(1)
        
    data = response.json()
    league_name = data['league']['name']
    
    results = data['standings']['results']
    if not results:
        print(f"Error: No standings results found for league ID {league_id}.", file=sys.stderr)
        sys.exit(1)
        
    num_to_fetch = min(len(results), top_n)
    standings = results[:num_to_fetch]
    
    top_players = []
    for player in standings:
        top_players.append({
            'entry_id': player['entry'],
            'player_name': player['player_name'],
            'entry_name': player['entry_name'],
            'total_points_current': player['total']
        })
    
    # Fetch history for each player
    all_players_history = []
    for player in top_players:
        print(f"Fetching history for {player['player_name']} ({player['entry_name']}) [ID: {player['entry_id']}]...")
        history_url = f"https://fantasy.premierleague.com/api/entry/{player['entry_id']}/history/"
        
        try:
            history_resp = requests_retry_get(history_url, headers=HEADERS)
        except Exception as e:
            print(f"Failed to fetch history for player ID {player['entry_id']}: {e}", file=sys.stderr)
            sys.exit(1)
            
        history_data = history_resp.json()
        
        # Sort history by event (gameweek)
        history_sorted = sorted(history_data['current'], key=lambda x: x['event'])
        
        events = [h['event'] for h in history_sorted]
        total_points = [h['total_points'] for h in history_sorted]
        
        all_players_history.append({
            'player_name': player['player_name'],
            'entry_name': player['entry_name'],
            'events': events,
            'points_history': total_points
        })
        
    return league_name, all_players_history

def generate_visualization(league_name, data, output_path, output_format, subframes, fps, freeze_frames):
    """Generate and save the animated visualization (MP4 or GIF)."""
    print(f"Generating animated {output_format.upper()}...")
    
    # Setup Matplotlib styling
    plt.rcParams['font.family'] = 'sans-serif'
    # Add Microsoft YaHei and SimHei for Chinese characters on Windows
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'DejaVu Sans', 'Arial', 'Helvetica']
    plt.rcParams['font.monospace'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'Menlo', 'Courier New', 'monospace']
    
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=150)
    fig.patch.set_facecolor('#111116')
    ax.set_facecolor('#16161f')
    
    num_players = len(data)
    num_gws = len(data[0]['events'])
    colors = get_colors(num_players)
    
    def format_name(player):
        return f"{player['player_name']} ({player['entry_name']})"
        
    labels = [format_name(p) for p in data]
    
    # Compute maximum points for axis limit
    max_pts = max(max(p['points_history']) for p in data)
    
    # Set up axis limits and styling
    ax.set_xlim(1, num_gws + 1.5)
    ax.set_ylim(0, max_pts + 100)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#333344')
    ax.spines['bottom'].set_color('#333344')
    ax.tick_params(colors='#a0aec0', which='both')
    ax.grid(color='#2d2d3d', linestyle='--', linewidth=0.5)
    
    ax.set_xlabel('Gameweek', color='#e2e8f0', fontsize=12, labelpad=10)
    ax.set_ylabel('Total Points', color='#e2e8f0', fontsize=12, labelpad=10)
    
    # Dynamic title using fetched league name
    ax.set_title(f'{league_name} Standing Progression', color='#ffffff', fontsize=15, pad=20, weight='bold')
    
    # Initialize components dynamically
    lines = []
    glows = []
    markers = []
    labels_text = []
    
    for i in range(num_players):
        l, = ax.plot([], [], color=colors[i], linewidth=3, label=labels[i], zorder=3)
        g, = ax.plot([], [], color=colors[i], linewidth=6, alpha=0.25, zorder=2)
        m = ax.scatter([], [], color=colors[i], s=80, edgecolor='#111116', linewidth=1.5, zorder=4)
        lbl = ax.text(0, 0, '', color=colors[i], fontweight='bold', fontsize=9, va='center')
        
        lines.append(l)
        glows.append(g)
        markers.append(m)
        labels_text.append(lbl)
        
    # Large background Gameweek text
    gw_bg_text = ax.text(0.5, 0.4, '', transform=ax.transAxes, color='#ffffff', alpha=0.04,
                         fontsize=100, fontweight='bold', ha='center', va='center', zorder=1)
                         
    # Standing Table box
    box_props = dict(boxstyle='round,pad=0.8', facecolor='#16161f', edgecolor='#333344', alpha=0.9, linewidth=1.5)
    table_text = ax.text(0.04, 0.93, '', transform=ax.transAxes, color='#e2e8f0', fontsize=9.5,
                          va='top', bbox=box_props, fontfamily='monospace', zorder=5)
                          
    # Interpolation setup
    x_raw = np.array(data[0]['events'])
    if subframes > 1:
        total_anim_frames = (num_gws - 1) * subframes + 1
        x_interp = np.linspace(1, num_gws, total_anim_frames)
        
        y_interp = []
        for player in data:
            y_interp.append(np.interp(x_interp, x_raw, player['points_history']))
    else:
        total_anim_frames = num_gws
        x_interp = x_raw
        y_interp = [np.array(player['points_history']) for player in data]
        
    total_frames = total_anim_frames + freeze_frames
    
    # Animation update loop
    def update(frame):
        idx = min(frame, total_anim_frames - 1)
        curr_x = x_interp[idx]
        
        x_data = x_interp[:idx+1]
        current_points = []
        
        for i in range(num_players):
            y_data = y_interp[i][:idx+1]
            
            lines[i].set_data(x_data, y_data)
            glows[i].set_data(x_data, y_data)
            
            # Position markers
            markers[i].set_offsets([[curr_x, y_data[-1]]])
            
            # Position labels
            labels_text[i].set_position((curr_x + 0.3, y_data[-1]))
            labels_text[i].set_text(f"{int(np.round(y_data[-1]))} pts")
            
            current_points.append(y_data[-1])
            
        curr_gw = int(np.round(curr_x))
        gw_bg_text.set_text(f"GW {curr_gw}")
        
        # Format standings table
        current_scores = []
        for i, player in enumerate(data):
            current_scores.append((player['player_name'], player['entry_name'], current_points[i]))
        current_scores.sort(key=lambda x: x[2], reverse=True)
        
        leaderboard_lines = [f"GW {curr_gw:02d} LEADERBOARD"]
        leaderboard_lines.append("-" * 35)
        for rank, (player_name, entry_name, pts) in enumerate(current_scores, 1):
            disp_name = f"{player_name} ({entry_name})"
            if len(disp_name) > 22:
                disp_name = disp_name[:19] + "..."
            leaderboard_lines.append(f"{rank}. {disp_name:<22} {int(np.round(pts)):>4} pts")
            
        table_text.set_text("\n".join(leaderboard_lines))
        
        # Rescale Y limits dynamically
        all_y_so_far = [y_interp[i][:idx+1] for i in range(num_players)]
        curr_max_y = max(max(y) for y in all_y_so_far)
        curr_min_y = min(min(y) for y in all_y_so_far)
        ax.set_ylim(max(0, curr_min_y - 50), curr_max_y + 60)
        
        return lines + glows + markers + labels_text + [gw_bg_text, table_text]
        
    # Dynamically scale legend layout and position to avoid overlapping
    legend_cols = min(4, num_players)
    legend_rows = (num_players + legend_cols - 1) // legend_cols
    anchor_y = -0.12 - (0.06 * legend_rows)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, anchor_y), ncol=legend_cols, 
              facecolor='#16161f', edgecolor='#333344', labelcolor='#e2e8f0', frameon=True, fontsize=8.5)
              
    fig.tight_layout()
    
    ani = animation.FuncAnimation(fig, update, frames=total_frames, interval=1000 // fps if output_format == 'mp4' else 150, blit=False)
    
    # Save the file
    if output_format == 'mp4':
        ani.save(output_path, writer='ffmpeg', fps=fps, extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])
    else:
        ani.save(output_path, writer='pillow', fps=fps)
        
    plt.close(fig)
    print(f"Successfully generated standings visualization saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="FPL Standings Progression Visualizer")
    parser.add_argument("-l", "--league-id", type=int, default=258110, help="FPL Classic League ID (default: 258110)")
    parser.add_argument("-f", "--format", choices=["mp4", "gif"], default="mp4", help="Output format: mp4 or gif (default: mp4)")
    parser.add_argument("-o", "--output", type=str, help="Output file path (default: fpl_standings_<league_id>.<format> in script dir)")
    parser.add_argument("-t", "--top", type=int, default=3, help="Number of top teams to visualize (default: 3)")
    parser.add_argument("--fps", type=int, help="Frames per second (defaults: 24 for mp4, 7 for gif)")
    parser.add_argument("-s", "--subframes", type=int, help="Interpolated frames between gameweeks (default: 8 for mp4, 1 for gif)")
    parser.add_argument("--freeze", type=int, help="Number of freeze frames at the end (default: 48 for mp4, 30 for gif)")
    
    args = parser.parse_args()
    
    # Setup default paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_format = args.format.lower()
    
    if args.output:
        output_path = args.output
        # Ensure output directory exists
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
    else:
        output_path = os.path.join(script_dir, f"fpl_standings_{args.league_id}.{output_format}")
        
    # Configure default parameters based on format
    if output_format == "mp4":
        fps = args.fps or 24
        subframes = args.subframes or 8
        freeze = args.freeze or 48
    else:
        fps = args.fps or 7
        subframes = args.subframes or 1
        freeze = args.freeze or 30
        
    # Fetch API Data
    league_name, data = fetch_data(args.league_id, args.top)
    
    # Generate Output
    generate_visualization(league_name, data, output_path, output_format, subframes, fps, freeze)

if __name__ == "__main__":
    main()
