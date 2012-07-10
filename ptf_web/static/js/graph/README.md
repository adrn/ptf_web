Graph
=====

There are many good Javascript/HTML5 graphing libraries already in existence e.g. [Flot](https://github.com/flot/flot), [D3](http://mbostock.github.com/d3/) and [Ico](https://github.com/alexyoung/ico). However they don't make the simple xy data graphs, often used in scientific environments, without extra plugins. I decided to write my own, small, graphing library that could deal with large amounts of data as well as logarithmic axes and page resizing. This was created as part of my work at Las Cumbres Observatory Global Telescope (LCOGT). [View demos and usage](http://slowe.github.com/graph/).


Dependencies
------------

For this library to work it has two dependencies:

* [jquery.js](http://jquery.com/) -- your site may already use this excellent library;
* [excanvas.js](http://code.google.com/p/explorercanvas/) -- this is used to allow canvas support on Internet Explorer (41.6 kB). If only it wasn't needed.


Features
--------
* Draws x/y graphs
* Can include error bars
* Both axes (or just one) can be logarithmic
* Multiple data series can be drawn with the following options:
  * Colour
  * Points shown or hidden
  * Points can be joined with lines
  * Line widths can be defined
  * Main plot area background colour can be set
  * Hover text on data points which can include custom text with replacable elements
* On newer versions of FF/Safari/Chrome the graph can be made full-screen by double clicking
* The graph inherits the font size/family from its parent elemet in the DOM (i.e. you can set it in the CSS)
* Can zoom in (click/drag) and zoom out (click)


Limitations
-----------
Some features (e.g. fullscreen) are experimental and will only work in the latest versions of modern browsers.


Author
------
Stuart Lowe works for the [Las Cumbres Observatory Global Telescope](http://lcogt.net/). LCOGT is a private operating foundation, building a global network of telescopes for professional research and citizen investigations.

