# Mood Badger

Show how you feel on your Badger 2350 or Tufty 2350. Each mood is a picture and a word. On the Badger the e-ink screen keeps showing it while the badge sleeps; on the Tufty the same pictures are shown larger, and the screen dims instead of going dark. A port of [MoodBadger](https://github.com/simonpainter/MoodBadger) for the Badger 2040.

Requires Badger 2350 or Tufty 2350 firmware **v3.1.1** or later. The same app folder runs on both.

## Controls

- **UP** / **DOWN**: previous / next mood
- **A** / **C**: previous / next mood set (the ◀ ▶ arrows in the bottom corners; hidden, and the buttons do nothing, with only one set)
- **HOME**: back to the menu

## On a Badger 2350

Hold a button until the screen starts to change; a quick tap during a refresh can be missed. On battery the badge sleeps after 5 seconds, and the e-ink keeps showing the mood. Any front button wakes it, and that press counts: DOWN wakes it and moves to the next mood.

## On a Tufty 2350

The buttons are the same. The screen is at full brightness after any press and dims after 10 seconds without one: to about half on USB power, to about 15% on battery. It never goes dark, so the mood is always visible. A press on a dimmed screen only brightens it; the next press changes the mood. The press that turns the badge on also only shows the saved mood.

The Tufty doesn't switch itself off. To turn it off, hold RESET on the back until the case lights fade; any front button turns it on again.

To have it open Mood Badger when it is turned on or reset, with HOME still opening the menu, install with `python3 -m tools.install --start-in-app --eject` (see the main README).

## Changing the moods

Edit `config.json` in this folder. `moods` is a list of mood sets; each mood is `[label, image]`, with images in `assets/`. `initial` is optional and sets the mood each set opens on. A set can hold up to 16 moods. To add or remove a set, add or delete its list in `moods` (and its `initial` entry); a single set is fine.

```json
{
  "moods": [
    [
      ["Chilled", "fig_chilled.png"],
      ["Sad", "fig_sad.png"]
    ],
    [
      ["Agree", "thumb_up.png"],
      ["Disagree", "thumb_down.png"]
    ]
  ],
  "initial": [0, 0]
}
```

Images look best at 122×136 pixels in black, white and two greys. The Tufty shows them 1.5 times larger.

## Credits

The mood images are [Google Material icons](https://fonts.google.com/icons), chosen for [MoodBadger](https://github.com/simonpainter/MoodBadger), and licensed under the Apache License 2.0 (see `assets/LICENSE`). The code is MIT-licensed.
