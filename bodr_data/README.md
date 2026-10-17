# BODR data files

Each `*.json` file in this folder is one design code. The BODR page loads every file automatically,
so adding a code means adding a file. Any section can be left out; its tab then shows "no table yet".

```json
{
  "code": "AASHTO",
  "full_name": "AASHTO Green Book",
  "order": 1,
  "k_values": {
    "source": "table name / edition",
    "speeds": [20, 30],
    "crest": [1, 2],
    "sag": [3, 6]
  },
  "horizontal": {
    "source": "table name / edition",
    "title": "short description",
    "e": [-2.0, 0.0, 2.0],
    "radii": { "20": [10, 9, 9], "30": [27, 25, 24] }
  },
  "turning": {
    "source": "table name / edition",
    "vehicles": [
      { "type": "Passenger Car", "symbol": "P", "min_radius": 7.26, "ctr": 6.4,
        "inside_radius": 4.39, "image": "Passenger Car Turning Radius.png" }
    ]
  }
}
```

Rules: lists in `radii` must have the same length as `e`; `crest` and `sag` the same length as `speeds`;
`image` is a file in the repository root (optional).
