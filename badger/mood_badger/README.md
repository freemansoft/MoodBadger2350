# Mood Badger

Show how you feel on your Badger 2350. Each mood is a picture and a word, and the e-ink screen keeps showing it while the badge sleeps. A port of [MoodBadger](https://github.com/simonpainter/MoodBadger) for the Badger 2040.

Requires Badger 2350 firmware **v3.1.1** or later.

## Controls

- **UP** / **DOWN**: previous / next mood
- **A** / **C**: previous / next mood set (the ◀ ▶ arrows in the bottom corners)
- **HOME**: back to the menu

Hold a button until the screen starts to change; a quick tap during a refresh can be missed. On battery the badge sleeps after 5 seconds, and any front button wakes it and moves straight to the next mood.

## Changing the moods

Edit `config.json` in this folder. `moods` is a list of mood sets; each mood is `[label, image]`, with images in `assets/`. `initial` is optional and sets the mood each set opens on. A set can hold up to 16 moods.

```json
{
  "moods": [
    [["Chilled", "happy.png"], ["Sad", "sad.png"]],
    [["Agree", "thumb_up.png"], ["Disagree", "thumb_down.png"]]
  ],
  "initial": [0, 0]
}
```

Images look best at 122×136 pixels in black, white and two greys.
