Generate a starting board for Settlers of Catan. Written in python 3.3 with
tkinter.

	$ python3 main.py

Settlers of Catan provides for several different ways of creating a starting
board depending on how randomized versus how fair you want the resources and
ports to be.  This tool allows you to select your level of randomization and
generate a new board with a single click.  Even with randomization of resource
values and ports, the algorithm will ensure a relatively fair board by ensuring
that the red values (6 and 8) are never placed together.

![Screenshot](/doc/images/screenshot.png)

Next
----

* Add a legend.
* Use (bmp/png) images for the tiles.
* Starting boards for expansion packs and game variants.
