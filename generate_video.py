import os
import requests
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import imageio_ffmpeg
import numpy as np

# Set up headers to mimic browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Tell matplotlib where ffmpeg is
plt.rcParams['animation.ffmpeg_path'] = imageio_ffmpeg.get_ffmpeg_exe()

def fetch_data():
    print("Fetching league standings...")
    league_url = "https://fantasy.premierleague.com/api/leagues-classic/258110/standings/"
    response = requests.get(league_url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    
    standings = data['standings']['results'][:3]
    top_3 = []
    for player in standings:
        top_3.append({
            'entry_id': player['entry'],
            'player_name': player['player_name'],
            'entry_name': player['entry_name'],
            'total_points_current': player['total']
        })
    
    # Fetch history for each player
    all_players_history = []
    for player in top_3:
        print(f"Fetching history for {player['player_name']} (ID: {player['entry_id']})...")
        history_url = f"https://fantasy.premierleague.com/api/entry/{player['entry_id']}/history/"
        history_resp = requests.get(history_url, headers=HEADERS)
        history_resp.raise_for_status()
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
        
    return all_players_history

def generate_video(data, output_path):
    print("Generating animated video...")
    # Styling configuration
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'DejaVu Sans', 'Arial', 'Helvetica']
    plt.rcParams['font.monospace'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'Menlo', 'Courier New', 'monospace']
    
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=150)
    fig.patch.set_facecolor('#111116')
    ax.set_facecolor('#16161f')
    
    # Extract players and data
    p1, p2, p3 = data[0], data[1], data[2]
    num_gws = len(p1['events'])
    
    # Colors for each player (Neon palette)
    colors = ['#00f5d4', '#ff007f', '#fee440']
    
    # Custom names for display
    def format_name(player):
        return f"{player['player_name']} ({player['entry_name']})"
    
    p1_label = format_name(p1)
    p2_label = format_name(p2)
    p3_label = format_name(p3)
    
    # Compute axis limits
    max_pts = max(max(p1['points_history']), max(p2['points_history']), max(p3['points_history']))
    
    # Setup axis styling
    ax.set_xlim(1, num_gws + 1.5) # extra space on right for labels
    ax.set_ylim(0, max_pts + 100)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#333344')
    ax.spines['bottom'].set_color('#333344')
    ax.tick_params(colors='#a0aec0', which='both')
    ax.grid(color='#2d2d3d', linestyle='--', linewidth=0.5)
    
    ax.set_xlabel('Gameweek', color='#e2e8f0', fontsize=12, labelpad=10)
    ax.set_ylabel('Total Points', color='#e2e8f0', fontsize=12, labelpad=10)
    ax.set_title('FPL 25/26 Mini-League Top 3 Standing Progression', color='#ffffff', fontsize=15, pad=20, weight='bold')
    
    # Lines and labels initialized
    line1, = ax.plot([], [], color=colors[0], linewidth=3, label=p1_label, zorder=3)
    line2, = ax.plot([], [], color=colors[1], linewidth=3, label=p2_label, zorder=3)
    line3, = ax.plot([], [], color=colors[2], linewidth=3, label=p3_label, zorder=3)
    
    # Glow effect lines (wider line, lower opacity)
    glow1, = ax.plot([], [], color=colors[0], linewidth=6, alpha=0.25, zorder=2)
    glow2, = ax.plot([], [], color=colors[1], linewidth=6, alpha=0.25, zorder=2)
    glow3, = ax.plot([], [], color=colors[2], linewidth=6, alpha=0.25, zorder=2)
    
    # End markers
    marker1 = ax.scatter([], [], color=colors[0], s=80, edgecolor='#111116', linewidth=1.5, zorder=4)
    marker2 = ax.scatter([], [], color=colors[1], s=80, edgecolor='#111116', linewidth=1.5, zorder=4)
    marker3 = ax.scatter([], [], color=colors[2], s=80, edgecolor='#111116', linewidth=1.5, zorder=4)
    
    # Dynamic labels at the end of each line
    lbl1 = ax.text(0, 0, '', color=colors[0], fontweight='bold', fontsize=9, va='center')
    lbl2 = ax.text(0, 0, '', color=colors[1], fontweight='bold', fontsize=9, va='center')
    lbl3 = ax.text(0, 0, '', color=colors[2], fontweight='bold', fontsize=9, va='center')
    
    # Large background Gameweek text
    gw_bg_text = ax.text(0.5, 0.4, '', transform=ax.transAxes, color='#ffffff', alpha=0.04,
                         fontsize=100, fontweight='bold', ha='center', va='center', zorder=1)
    
    # Standing Table box
    box_props = dict(boxstyle='round,pad=0.8', facecolor='#16161f', edgecolor='#333344', alpha=0.9, linewidth=1.5)
    table_text = ax.text(0.04, 0.93, '', transform=ax.transAxes, color='#e2e8f0', fontsize=9.5,
                         va='top', bbox=box_props, fontfamily='monospace', zorder=5)
    
    # Set up smooth interpolation
    subframes = 8
    x_raw = np.array(p1['events'])
    total_anim_frames = (num_gws - 1) * subframes + 1
    x_interp = np.linspace(1, num_gws, total_anim_frames)
    
    y1_interp = np.interp(x_interp, x_raw, p1['points_history'])
    y2_interp = np.interp(x_interp, x_raw, p2['points_history'])
    y3_interp = np.interp(x_interp, x_raw, p3['points_history'])
    
    # Total frames: anim frames + 2 seconds freeze at 24fps
    fps = 24
    freeze_frames = 48
    total_frames = total_anim_frames + freeze_frames
    
    # Animation update function
    def update(frame):
        idx = min(frame, total_anim_frames - 1)
        curr_x = x_interp[idx]
        
        # Sliced data for lines
        x_data = x_interp[:idx+1]
        y1_data = y1_interp[:idx+1]
        y2_data = y2_interp[:idx+1]
        y3_data = y3_interp[:idx+1]
        
        # Update main lines
        line1.set_data(x_data, y1_data)
        line2.set_data(x_data, y2_data)
        line3.set_data(x_data, y3_data)
        
        # Update glow lines
        glow1.set_data(x_data, y1_data)
        glow2.set_data(x_data, y2_data)
        glow3.set_data(x_data, y3_data)
        
        # Update markers at current interpolated position
        marker1.set_offsets([[curr_x, y1_data[-1]]])
        marker2.set_offsets([[curr_x, y2_data[-1]]])
        marker3.set_offsets([[curr_x, y3_data[-1]]])
        
        # Update inline labels (offset slightly to the right)
        lbl1.set_position((curr_x + 0.3, y1_data[-1]))
        lbl1.set_text(f"{int(np.round(y1_data[-1]))} pts")
        
        lbl2.set_position((curr_x + 0.3, y2_data[-1]))
        lbl2.set_text(f"{int(np.round(y2_data[-1]))} pts")
        
        lbl3.set_position((curr_x + 0.3, y3_data[-1]))
        lbl3.set_text(f"{int(np.round(y3_data[-1]))} pts")
        
        # Update background GW text (show integer GW based on current position)
        curr_gw = int(np.round(curr_x))
        gw_bg_text.set_text(f"GW {curr_gw}")
        
        # Sort current standing for the leaderboard box
        current_scores = [
            (p1['player_name'], p1['entry_name'], y1_data[-1], colors[0]),
            (p2['player_name'], p2['entry_name'], y2_data[-1], colors[1]),
            (p3['player_name'], p3['entry_name'], y3_data[-1], colors[2])
        ]
        current_scores.sort(key=lambda x: x[2], reverse=True)
        
        # Create standing table content
        leaderboard_lines = [f"GW {curr_gw:02d} LEADERBOARD"]
        leaderboard_lines.append("-" * 35)
        for rank, (player_name, entry_name, pts, _) in enumerate(current_scores, 1):
            disp_name = f"{player_name} ({entry_name})"
            if len(disp_name) > 22:
                disp_name = disp_name[:19] + "..."
            leaderboard_lines.append(f"{rank}. {disp_name:<22} {int(np.round(pts)):>4} pts")
            
        table_text.set_text("\n".join(leaderboard_lines))
        
        # Adjust Y-limits dynamically based on min/max so far
        current_max = max(max(y1_data), max(y2_data), max(y3_data))
        current_min = min(min(y1_data), min(y2_data), min(y3_data))
        ax.set_ylim(max(0, current_min - 50), current_max + 60)
        
        return line1, line2, line3, glow1, glow2, glow3, marker1, marker2, marker3, lbl1, lbl2, lbl3, gw_bg_text, table_text

    # Create legend at the bottom
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.18), ncol=3, 
              facecolor='#16161f', edgecolor='#333344', labelcolor='#e2e8f0', frameon=True)
    
    fig.tight_layout()
    
    # Set the animation (interval is milliseconds per frame)
    ani = animation.FuncAnimation(fig, update, frames=total_frames, interval=1000 // fps, blit=False)
    
    # Save the animation as MP4 (H.264 codec, YUV420p color format for iOS/macOS compatibility)
    ani.save(output_path, writer='ffmpeg', fps=fps, extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])
    plt.close(fig)
    print(f"Video saved to {output_path}")

if __name__ == "__main__":
    data = fetch_data()
    output_dir = "/Users/liyiyuan/.gemini/antigravity/scratch/fpl_standing_gif"
    output_file = os.path.join(output_dir, "fpl_standings_progression.mp4")
    generate_video(data, output_file)
