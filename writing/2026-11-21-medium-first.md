# Too much light pollution for amateur astronomy where you live? Think again!

*And you can do it cheaply, without standing around outside*

![medium-startrails.jpg](medium-startrails.jpg)
*One clear night over a London suburb, 7-8 October 2026: 662 one-minute
frames from a £25 camera, combined into one picture.*

Astrophotography advice starts with "find a dark site". I live in suburban
London, where the sky glows orange, there are trees and house lights in the
way, and I have a budget closer to a Raspberry Pi than a remote observatory.
So I am trying the other way round: if I cannot have a dark sky, I can have a
long one. And I do not have to be out there: the cameras run every night on
their own while I sleep.

## The idea: a long time baseline

A single exposure here is short, 12 to 60 seconds, before the town's glow
fills it. But a camera that stays pointed at the same patch of sky every clear
night for a month collects hundreds of hours of light. Stack all of it and the
faint things the glow hides, one night at a time, start to show.

The goal is one picture, made from a month of nights.

## The kit

- Small Pi cameras on Raspberry Pis, in the garden and at a window, aimed
  near the celestial pole
- A home server that stacks each night's frames the next morning
- Photos, stacks and a nightly "how dark was it" chart published on my
  website

## What the sky taught me first

- **Cloud is brighter than twilight here.** Low cloud lit from below by the
  town outshines dusk, so my software was first picking the "darkest" part of
  the night inside the evening twilight. It now looks only after the Sun is
  18 degrees down.
- **The stars turn.** Over a night everything rotates around the pole, so
  frames must be de-rotated before they can be added. Across a month it is
  harder still, because the cameras get nudged and the lens distortion has to
  be modelled.
- **A good night is worth recording.** I keep one clear July night as my
  reference for how dark this sky can get, and every night since is charted
  against it.
- **Hardware has opinions.** A month of frames is about half a terabyte, and
  my stacking server once cut out because its fan had stopped and its CPU
  reached 97 C in seconds.

## Where it stands

![medium-deep.jpg](medium-deep.jpg)
*The same night with the sky's rotation removed and the frames stacked: far
more stars than the orange glow lets you see by eye.*

A single night's stack already reaches stars around magnitude 9.7 near the
pole, from a garden where you can see perhaps a few dozen by eye. The
month-long stack is next.

Every night's results are public, clear or cloudy:
[www.petergrecian.co.uk/astro](https://www.petergrecian.co.uk/astro?ref=medium)

If you are imaging from a city on a budget, I would love to hear what you are
trying.
