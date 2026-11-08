import csv
import sys
import os
import glob
import matplotlib.pyplot as plt

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")

if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    files = glob.glob(os.path.join(LOG_DIR, "*.csv"))
    if not files:
        print(f"No CSV files in {LOG_DIR}")
        sys.exit(1)
    path = max(files, key=os.path.getmtime)

print(f"Reading {path}")

with open(path, newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    print("File is empty.")
    sys.exit(1)

def column(rows, name):
    values = []
    for row in rows:
        if name == "t_s":
            values.append(float(row[name]))
        else:
            values.append(int(row[name]))
    return values


def first_time(rows, name, value, after):
    if after is None:
        return None
    for row in rows:
        t = float(row["t_s"])
        if t >= after and int(row[name]) == value:
            return t
    return None


def draw_lanes(ax, rows, t, names):
    for lane, name in enumerate(names):
        values = column(rows, name)
        y = []
        for v in values:
            y.append(v * 0.8 + lane)
        ax.step(t, y, where="post", label=name)
    ax.set_yticks([lane + 0.4 for lane in range(len(names))])
    ax.set_yticklabels(names)
    ax.set_ylim(-0.2, len(names))
    ax.grid(True, axis="x", alpha=0.3)

t = column(rows, "t_s")

fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 7))

ax = axes[0]
ax.plot(t, column(rows, "u_main_mv"), label="U_MAIN")
ax.plot(t, column(rows, "u_backup_mv"), label="U_BACKUP")
ax.axhline(1700, linestyle="--", color="green", label="OK (1700 mV)")
ax.axhline(250, linestyle="--", color="red", label="broken wire (250 mV)")
ax.set_ylabel("mV")
ax.legend(loc="upper right", fontsize=8)
ax.grid(True, alpha=0.3)

draw_lanes(axes[1], rows, t, ["MAIN_LOST", "WANT_BACKUP", "Q1_CLOSED", "Q2_CLOSED"])

draw_lanes(axes[2], rows, t, ["Q1_CLOSE_CMD", "Q1_OPEN_CMD", "Q2_CLOSE_CMD", "Q2_OPEN_CMD"])
axes[2].set_xlabel("t (s)")

fig.suptitle(os.path.basename(path))
fig.tight_layout()

t_main_lost = first_time(rows, "MAIN_LOST", 1, 0)
t_q1_open   = first_time(rows, "Q1_CLOSED", 0, t_main_lost)
t_q2_closed = first_time(rows, "Q2_CLOSED", 1, t_main_lost)
t_back_off  = first_time(rows, "WANT_BACKUP", 0, t_q2_closed)
t_q2_open   = first_time(rows, "Q2_CLOSED", 0, t_back_off)
t_q1_closed = first_time(rows, "Q1_CLOSED", 1, t_q2_open)


def show(label, end, start):
    if end is None or start is None:
        print(f"{label:22s}: not found in this log")
    else:
        print(f"{label:22s}: {end - start:.2f} s")


show("transfer time", t_q2_closed, t_main_lost)
show("dead time (transfer)", t_q2_closed, t_q1_open)
show("dead time (return)", t_q1_closed, t_q2_open)

png_path = os.path.splitext(path)[0] + ".png"
fig.savefig(png_path, dpi=150)
print(f"Saved {png_path}")

plt.show()