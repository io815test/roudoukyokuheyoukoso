from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "world_seed_points_map_4x3.png"


SEED_POINTS = [
    {
        "name": "イラン播種点",
        "detail": "ヤースージュ近郊",
        "lon": 51.59,
        "lat": 30.67,
        "label_lon": 34,
        "label_lat": 38,
        "align": "right",
    },
    {
        "name": "東欧播種点",
        "detail": "南ウクライナ・黒海北岸",
        "lon": 32.0,
        "lat": 47.0,
        "label_lon": 5,
        "label_lat": 54,
        "align": "right",
    },
    {
        "name": "シベリア播種点",
        "detail": "西シベリア中部・トムスク北方",
        "lon": 84.5,
        "lat": 58.5,
        "label_lon": 106,
        "label_lat": 64,
        "align": "left",
    },
    {
        "name": "アフリカ播種点",
        "detail": "コンゴ盆地",
        "lon": 23.0,
        "lat": -2.0,
        "label_lon": -6,
        "label_lat": -18,
        "align": "right",
    },
    {
        "name": "東南アジア播種点",
        "detail": "インドネシア〜マレーシア",
        "lon": 113.0,
        "lat": 1.0,
        "label_lon": 136,
        "label_lat": 12,
        "align": "left",
    },
]


CONTINENTS = [
    [(-168, 72), (-140, 72), (-120, 68), (-104, 62), (-92, 54), (-82, 48), (-84, 27), (-96, 18), (-110, 20), (-118, 28), (-124, 36), (-138, 53), (-156, 58), (-168, 72)],
    [(-82, 12), (-68, 8), (-52, 2), (-44, -10), (-50, -24), (-58, -34), (-64, -50), (-72, -56), (-78, -46), (-80, -18), (-82, 12)],
    [(-73, 82), (-28, 82), (-18, 75), (-30, 64), (-50, 60), (-60, 66), (-73, 82)],
    [(-10, 72), (20, 72), (46, 66), (66, 60), (88, 55), (116, 56), (142, 48), (156, 38), (160, 28), (152, 16), (132, 10), (118, 0), (104, 6), (94, 16), (78, 24), (68, 25), (60, 16), (48, 14), (40, 24), (28, 36), (18, 44), (10, 46), (2, 52), (-6, 60), (-10, 72)],
    [(-18, 35), (4, 36), (18, 32), (30, 22), (34, 6), (30, -10), (20, -24), (10, -34), (-4, -34), (-12, -20), (-16, 2), (-18, 20), (-18, 35)],
    [(112, -10), (154, -10), (154, -42), (128, -45), (114, -28), (112, -10)],
    [(42, 30), (58, 30), (66, 24), (56, 14), (44, 18), (42, 30)],
    [(96, 22), (108, 18), (114, 6), (108, -6), (98, -2), (92, 10), (96, 22)],
]


def pick_font() -> FontProperties | None:
    candidates = [
        Path("C:/Windows/Fonts/YuGothM.ttc"),
        Path("C:/Windows/Fonts/YuGothB.ttc"),
        Path("C:/Windows/Fonts/meiryo.ttc"),
        Path("C:/Windows/Fonts/msgothic.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return FontProperties(fname=str(path))
    return None


def add_world(ax):
    ocean = "#d9ecf5"
    land = "#efe4c8"
    coast = "#6c7166"
    grid = "#b7cad1"

    ax.set_facecolor(ocean)
    for lon in range(-180, 181, 30):
        ax.plot([lon, lon], [-60, 85], color=grid, lw=0.7, alpha=0.7, zorder=0)
    for lat in range(-60, 91, 15):
        ax.plot([-180, 180], [lat, lat], color=grid, lw=0.7, alpha=0.7, zorder=0)

    for poly in CONTINENTS:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        ax.fill(xs, ys, facecolor=land, edgecolor=coast, linewidth=1.2, zorder=1)

    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)
    ax.set_aspect("auto")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def add_seed_points(ax, font):
    marker_fill = "#d94841"
    marker_outer = "#8f1d1d"
    callout = "#7a5130"
    text_color = "#2f261f"

    for point in SEED_POINTS:
        ax.scatter(point["lon"], point["lat"], s=210, color=marker_outer, alpha=0.22, zorder=4)
        ax.scatter(point["lon"], point["lat"], s=90, color=marker_fill, edgecolor="white", linewidth=1.5, zorder=5)
        ax.plot(
            [point["lon"], point["label_lon"]],
            [point["lat"], point["label_lat"]],
            color=callout,
            lw=1.2,
            zorder=3,
        )

        ha = "right" if point["align"] == "right" else "left"
        ax.text(
            point["label_lon"],
            point["label_lat"] + 2.2,
            point["name"],
            ha=ha,
            va="bottom",
            fontsize=12.5,
            color=text_color,
            fontproperties=font,
            weight="bold",
            zorder=6,
        )
        ax.text(
            point["label_lon"],
            point["label_lat"] - 0.8,
            point["detail"],
            ha=ha,
            va="top",
            fontsize=9.8,
            color=text_color,
            fontproperties=font,
            zorder=6,
        )


def add_frame_text(fig, font):
    title_color = "#2b2924"
    sub_color = "#5e5448"

    fig.text(
        0.06,
        0.94,
        "五播種点マップ",
        fontsize=24,
        color=title_color,
        fontproperties=font,
        weight="bold",
    )
    fig.text(
        0.06,
        0.905,
        "canon/01_core_and_history.md の五播種点設定に基づく位置図",
        fontsize=11,
        color=sub_color,
        fontproperties=font,
    )
    fig.text(
        0.06,
        0.055,
        "比率 4:3 / 横長",
        fontsize=10,
        color=sub_color,
        fontproperties=font,
    )


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    font = pick_font()

    fig = plt.figure(figsize=(12, 9), dpi=160)
    ax = fig.add_axes([0.04, 0.12, 0.92, 0.76])

    add_world(ax)
    add_seed_points(ax, font)
    add_frame_text(fig, font)

    fig.savefig(OUT, dpi=160)
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
