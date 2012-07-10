/*
	LCOGT jQuery graphing library.
	Written by Stuart Lowe (LCOGT)
	
	INCLUDES:
	* Fix for setTimeout in IE - http://webreflection.blogspot.com/2007/06/simple-settimeout-setinterval-extra.html
	* Full screen API - http://johndyer.name/native-fullscreen-javascript-api-plus-jquery-plugin/
	
	USAGE:
		<html>
		<head>
			<!--[if lt IE 9]><script src="excanvas.js" type="text/javascript"></script><![endif]-->
			<script src="jquery.min.js" type="text/javascript"></script>
			<script src="jquery.graph.js" type="text/javascript"></script>
			<script type="text/javascript">
			<!--
				$(document).ready(function(){
					// Each point in this example consists of [x,y,uncertainty] but can be [x,y] and [x,y,plus,minus]
					series = [[1,0.999,0.022],[2,1.002,0.012],[3,0.999,0.012],[4,0.997,0.013],[5,0.999,0.03]];
					graph = $.graph('lightcurve', {
						data: series,
						color: "#dd9901",
						points: {show:true,radius:1.5},
						lines:{show:false,width:4}
					}, {
						xaxis: {log:false,label:'t'},
						grid: {show:false,color:'rgb(255,0,0)',background:'rgb(255,255,255)'}
					});
	
				});
			//-->
			</script>
		</head>
		<body>
			<div id="lightcurve" style="width:100%;height:350px;font-size:0.8em;font-family:Century Gothic,sans-serif;"></div>
		</body>
		</html>
*/

(function($) {

	// First we will include all the useful helper functions
	
	/*@cc_on
	// Fix for IE's inability to handle arguments to setTimeout/setInterval
	// From http://webreflection.blogspot.com/2007/06/simple-settimeout-setinterval-extra.html
	(function(f){
		window.setTimeout =f(window.setTimeout);
		window.setInterval =f(window.setInterval);
	})(function(f){return function(c,t){var a=[].slice.call(arguments,2);return f(function(){c.apply(this,a)},t)}});
	@*/

	// Full Screen API - http://johndyer.name/native-fullscreen-javascript-api-plus-jquery-plugin/
	var fullScreenApi = {
		supportsFullScreen: false,
		isFullScreen: function() { return false; },
		requestFullScreen: function() {},
		cancelFullScreen: function() {},
		fullScreenEventName: '',
		prefix: ''
	},
	browserPrefixes = 'webkit moz o ms khtml'.split(' ');
	// check for native support
	if (typeof document.cancelFullScreen != 'undefined') {
		fullScreenApi.supportsFullScreen = true;
	} else {
		// check for fullscreen support by vendor prefix
		for (var i = 0, il = browserPrefixes.length; i < il; i++ ) {
			fullScreenApi.prefix = browserPrefixes[i];
			if (typeof document[fullScreenApi.prefix + 'CancelFullScreen' ] != 'undefined' ) {
				fullScreenApi.supportsFullScreen = true;
				break;
			}
		}
	}
	// update methods to do something useful
	if (fullScreenApi.supportsFullScreen) {
		fullScreenApi.fullScreenEventName = fullScreenApi.prefix + 'fullscreenchange';
		fullScreenApi.isFullScreen = function() {
			switch (this.prefix) {
				case '':
					return document.fullScreen;
				case 'webkit':
					return document.webkitIsFullScreen;
				default:
					return document[this.prefix + 'FullScreen'];
			}
		}
		fullScreenApi.requestFullScreen = function(el) {
			return (this.prefix === '') ? el.requestFullScreen() : el[this.prefix + 'RequestFullScreen']();
		}
		fullScreenApi.cancelFullScreen = function(el) {
			return (this.prefix === '') ? document.cancelFullScreen() : document[this.prefix + 'CancelFullScreen']();
		}
	}
	// jQuery plugin
	if (typeof jQuery != 'undefined') {
		jQuery.fn.requestFullScreen = function() {
			return this.each(function() {
				if (fullScreenApi.supportsFullScreen) {
					fullScreenApi.requestFullScreen(this);
				}
			});
		};
	}
	// export api
	window.fullScreenApi = fullScreenApi;
	// End of Full Screen API

	// Extra mathematical/helper functions that will be useful - inspired by http://alexyoung.github.com/ico/
	var G = {};
	G.sum = function(a) { var i, sum; for (i = 0, sum = 0; i < a.length; sum += a[i++]) {}; return sum; };
	if (typeof Array.prototype.max === 'undefined') G.max = function(a) { return Math.max.apply({}, a); };
	else G.max = function(a) { return a.max(); };
	if (typeof Array.prototype.min === 'undefined') G.min = function(a) { return Math.min.apply({}, a); };
	else G.min = function(a) { return a.min(); };
	G.mean = function(a) { return G.sum(a) / a.length; };
	G.stddev = function(a) { return Math.sqrt(G.variance(a)); };
	G.log10 = function(v) { return Math.log(v)/2.302585092994046; };
	G.variance = function(a) { var mean = G.mean(a), variance = 0; for (var i = 0; i < a.length; i++) variance += Math.pow(a[i] - mean, 2); return variance / (a.length - 1); };
	if (typeof Object.extend === 'undefined') {
		G.extend = function(destination, source) {
			for (var property in source) {
				if (source.hasOwnProperty(property)) destination[property] = source[property];
			}
			return destination;
		};
	} else G.extend = Object.extend;
	if (Object.keys) G.keys = Object.keys;
	else {
		G.keys = function(o) {
			if (o !== Object(o)) throw new TypeError('Object.keys called on non-object');
			var ret = [], p;
			for (p in o) {
				if (Object.prototype.hasOwnProperty.call(o,p)) ret.push(p);
			}
			return ret;
		}
	}

	// Define a shortcut for checking variable types
	function is(a,b){ return (typeof a == b) ? true : false; }

	// Convert a "#xxxxxx" colour into an "rgb(x,x,x)" colour
	function parseColour(c){
		if(c.indexOf('#')!=0) return c;
		//Easier to visualize bitshifts in hex
		rgb = parseInt(c.substr(1), 16);
		//Extract rgb info
		r = (rgb & (255 << 16)) >> 16;
		g = (rgb & (255 << 8)) >> 8;
		b = (rgb & 255);
		return "rgb("+r+","+g+","+b+")";
	}

	function zeroFill(number, width){
		width -= number.toString().length;
		if(width > 0) return new Array( width + (/\./.test( number ) ? 2 : 1) ).join( '0' ) + number;
		return number + ""; // always return a string
	}
	
	// Add commas every 10^3
	function addCommas(nStr) {
		nStr += '';
		var x = nStr.split('.');
		var x1 = x[0];
		var x2 = x.length > 1 ? '.' + x[1] : '';
		var rgx = /(\d+)(\d{3})/;
		while (rgx.test(x1)) x1 = x1.replace(rgx, '$1' + ',' + '$2');
		return x1 + x2;
	}

	// Get the current Julian Date
	function getJD(today) {
		// The Julian Date of the Unix Time epoch is 2440587.5
		if(!today) today = new Date();
		return ( today.getTime() / 86400000.0 ) + 2440587.5;
	}

	// A non-jQuery dependent function to get a style
	function getStyle(el, styleProp) {
		if (typeof window === 'undefined') return;
		var style;
		var el = document.getElementById(el);
		if (el.currentStyle) style = el.currentStyle[styleProp];
		else if (window.getComputedStyle) style = document.defaultView.getComputedStyle(el, null).getPropertyValue(styleProp);
		if (style && style.length === 0) style = null;
		return style;
	}
	// End of helper functions


	// Define the class to deal with <canvas>.
	function Canvas(i){
		if(!(typeof i=="string" || (typeof i=="object" && typeof i.id=="string"))) return;

		// Define default values
		this.id = '';
		this.canvas = '';
		this.c = '';
		this.wide = 0;
		this.tall = 0;
		this.fullscreen = false;
		this.fullwindow = false;
		this.transparent = false;
		this.color = "";
		this.background = "rgb(255,255,255)";
		this.events = {resize:""};	// Let's add some default events

		// Add options to detect for older IE
		this.ie = false;
		this.excanvas = (typeof G_vmlCanvasManager != 'undefined') ? true : false;
		/*@cc_on
		this.ie = true
		@*/

		// Overwrite defaults with variables passed to the function
		var n = "number";
		var s = "string";
		var b = "boolean";
		var o = "object";
		var f = "function";
		if(is(i.id,s)) this.id = i.id;
		if(is(i.background,s)) this.background = i.background;
		if(is(i.color,s)) this.color = i.color;
		if(is(i.width,n)) this.wide = i.width;
		if(is(i.height,n)) this.tall = i.height;
		if(is(i.fullwindow,b)) this.fullwindow = i.fullwindow;
		if(is(i.transparent,b)) this.transparent = i.transparent;

		if(!this.id) return;
		// Construct the <canvas> container
		this.container = $('#'+this.id);
		if(this.container.length == 0){
			// No appropriate container exists. So we'll make one.
			$('body').append('<div id="'+this.id+'"></div>');
			this.container = $('#'+this.id);
		}
		this.container.css('position','relative');
		$(window).bind("resize",{me:this},function(ev){ ev.data.me.resize(); });

		// If the Javascript function has been passed a width/height
		// those take precedence over the CSS-set values
		if(this.wide > 0) this.container.css('width',this.wide);
		this.wide = this.container.width();
		if(this.tall > 0) this.container.css('height',this.tall);
		this.tall = this.container.height();
	
		// Rename as the holder
		this.container.attr('id',this.id+'holder');
	
		// Add a <canvas> to it with the original ID
		this.container.html('<canvas id="'+this.id+'" style="display:block;font:inherit;"></canvas>');
		this.containerbg = this.container.css('background');
		this.canvas = $('#'+this.id);
		this.c = document.getElementById(this.id);
		// For excanvas we need to initialise the newly created <canvas>
		if(this.excanvas) this.c = G_vmlCanvasManager.initElement(this.c);
	
		if(this.c && this.c.getContext){  
			this.setWH(this.wide,this.tall);
			this.ctx = this.c.getContext('2d');
			this.ctx.clearRect(0,0,this.wide,this.tall);
			this.ctx.beginPath();
			var fs = 16;
			this.ctx.font = fs+"px sans-serif";
			this.ctx.fillStyle = 'rgb(0,0,0)';
			this.ctx.lineWidth = 1.5;
			var loading = 'Loading graph...';
			this.ctx.fillText(loading,(this.wide-this.ctx.measureText(loading).width)/2,(this.tall-fs)/2)
			this.ctx.fill();
		}

		// Bind events
		if(fullScreenApi.supportsFullScreen){
			// Bind the fullscreen function to the double-click event if the browser supports fullscreen
			this.canvas.bind('dblclick', {me:this}, function(e){ e.data.me.toggleFullScreen(); });
		}
		this.canvas.bind("mousedown",{me:this}, function(e){ e.data.me.trigger("mousedown",{event:e}); });
		this.canvas.bind("mousemove",{me:this}, function(e){ e.data.me.trigger("mousemove",{event:e}); });
		this.canvas.bind("mouseup",{me:this}, function(e){ e.data.me.trigger("mouseup",{event:e}); });
	}
	// Attach a handler to an event for the Canvas object in a style similar to that used by jQuery
	//   .bind(eventType[,eventData],handler(eventObject));
	//   .bind("resize",function(e){ console.log(e); });
	//   .bind("resize",{me:this},function(e){ console.log(e.data.me); });
	Canvas.prototype.bind = function(ev,e,fn){
		if(typeof ev!="string") return this;
		if(is(fn,"undefined")){
			fn = e;
			e = {};
		}else{
			e = {data:e}
		}
		if(typeof e!="object" || typeof fn!="function") return this;
		if(this.events[ev]) this.events[ev].push({e:e,fn:fn});
		else this.events[ev] = [{e:e,fn:fn}];
		return this;
	}
	// Trigger a defined event with arguments. This is for internal-use to be 
	// sure to include the correct arguments for a particular event
	Canvas.prototype.trigger = function(ev,args){
		if(typeof ev != "string") return;
		if(typeof args != "object") args = {};
		var o = [];
		if(typeof this.events[ev]=="object"){
			for(var i = 0 ; i < this.events[ev].length ; i++){
				var e = G.extend(this.events[ev][i].e,args);
				if(typeof this.events[ev][i].fn == "function") o.push(this.events[ev][i].fn.call(this,e))
			}
		}
		if(o.length > 0) return o;
	}
	Canvas.prototype.copyToClipboard = function(){
		this.clipboard = this.ctx.getImageData(0, 0, this.wide, this.tall);
		this.clipboardData = this.clipboard.data;
	}
	Canvas.prototype.pasteFromClipboard = function(){
		this.clipboard.data = this.clipboardData;
		this.ctx.putImageData(this.clipboard, 0, 0);
	}
	// Will toggle the <canvas> as a full screen element if the browser supports it.
	Canvas.prototype.toggleFullScreen = function(){
		if(fullScreenApi.supportsFullScreen) {
			this.elem = document.getElementById(this.id+"holder");
			if(fullScreenApi.isFullScreen()){
				fullScreenApi.cancelFullScreen(this.elem);
				this.fullscreen = false;
			}else{
				fullScreenApi.requestFullScreen(this.elem);
				this.fullscreen = true;
			}
		}
	}
	// A function to be called whenever the <canvas> needs to be resized.
	//   .resize();
	//   .resize(400,250)
	Canvas.prototype.resize = function(w,h){
		if(!this.canvas) return;
		if(!w || !h){
			// Reset the fullscreen toggle if necessary
			if(this.fullscreen && !fullScreenApi.isFullScreen()) this.fullscreen = false;
			if(this.fullscreen) this.container.css('background','white');
			else this.container.css('background',this.containerbg);
			
			if(this.fullwindow){
				this.canvas.css({'width':0,'height':0});
				w = $(window).width();
				h = $(window).height();
				this.canvas.css({'width':w,'height':h});
				$(document).css({'width':w,'height':h});
			}else{
				// We have to zap the width of the canvas to let it take the width of the container
				this.canvas.css({'width':0,'height':0});
				w = this.container.outerWidth();
				h = this.container.outerHeight();
				this.canvas.css({'width':w,'height':h});
			}
		}
		if(w == this.wide && h == this.tall) return;
		this.setWH(w,h);
		// Trigger callback
		this.trigger("resize",{w:w,h:h});
	}
	// Internal function to update the internal variables defining the width and height.
	Canvas.prototype.setWH = function(w,h,ctx){
		if(!w || !h) return;
		var c = (typeof ctx=="undefined") ? this.c : ctx;
		c.width = w;
		c.height = h;
		this.wide = w;
		this.tall = h;
		// Bug fix for IE 8 which sets a width of zero to a div within the <canvas>
		if(this.ie && $.browser.version == 8) $('#'+this.id).find('div').css({'width':w,'height':h});
		this.canvas.css({'width':w,'height':h});
	}


	// Now we define the Graph class
	// mygraph = $.graph(id, {data:series,color: "#9944ff",points:{show:false,radius:1.5},lines:{show:true,width:4}}, options);
	// where:
	//   id (string) is the ID of the HTML element to attach the canvas to
	//   series (array) contains the data series e.g. series = [[x,y],[x2,y2],[x3,y3],...[xn,yn]] or an array of data series;
	//   options (object) contains any customisation options for the graph as a whole e.g. options = { xaxis:{ label:'Time (HJD)' },yaxis: { label: 'Delta (mag)' }};
	function Graph(element, data, options){
		// Define some variables
		this.version = "0.1.2";
		this.logging = false;
		this.start = new Date();
		if(typeof element!="string") return;
		this.id = element;
		this.data = {};
		this.chart = {};
		this.options = {};
		this.selecting = false;
		this.events = [];
		this.lines = [];

		if(this.logging) var d = new Date();

		// Define the drawing canvas
		this.canvas = new Canvas({id:this.id});

		// Bind events to the canvas
		this.canvas.bind("resize",{me:this},function(ev){
			// Attach an event to deal with resizing the <canvas>
			if(ev.data.me.logging) var d = new Date();
			ev.data.me.setOptions().calculateData().draw().trigger("resize",{event:ev.event});
			if(ev.data.me.logging) console.log("Total until end of resize:" + (new Date() - d) + "ms");
		}).bind("mousedown",{me:this},function(ev){
			var g = ev.data.me;	// The graph object
			if(ev.event.which!=1) return;	// Only zoom on left click
			// Check if there is a data point at the position that the user clicked.
			d = g.dataAtMousePosition(ev.event.layerX,ev.event.layerY);
			if(is(d,"undefined")){
				// No data so we'll start the zoom selection
				if(g.within(ev.event.layerX,ev.event.layerY)){
					g.selectfrom = [ev.event.layerX,ev.event.layerY];
					g.selectto = g.selectfrom;
					g.selecting = true;
				}
				// Keep a copy of the current state of the canvas
				g.canvas.copyToClipboard();
			}else{
				// This is a data point so we'll trigger the clickpoint event
				s = parseInt(d[0]);
				i = parseInt(d[1]);
				d = g.data[s];
				ii = g.getPixPos(ev.event.layerX,ev.event.layerY);
				g.trigger("clickpoint",{event:ev.event,series:s,n:i,point:d.data[i],xpix:ev.event.layerX,ypix:ii[1],title:d.title,color:d.color});
			}
			return true;
		}).bind("mousemove",{me:this},function(ev){
			var g = ev.data.me;	// The graph object
			// Attach hover event
			if(!g.selecting){
				d = g.dataAtMousePosition(ev.event.layerX,ev.event.layerY);
				g.highlight(d);
				if(typeof d!="undefined"){
					s = d[0];
					i = d[1];
					d = g.data[s];
					g.trigger("hoverpoint",{event:ev.event,point:d.data[i],xpix:ev.event.layerX,ypix:ii[1],title:d.title,color:d.color});
				}
				if(g.events["mousemove"]){
					var pos = g.pixel2data(ev.event.layerX,ev.event.layerY);
					g.trigger("mousemove",{event:ev.event,x:pos.x,y:pos.y});
				}
			}else{
				if(g.within(ev.event.layerX,ev.event.layerY)){
					g.selectto = [ev.event.layerX,ev.event.layerY];
					g.canvas.pasteFromClipboard();
					// Draw selection rectangle
					g.canvas.ctx.beginPath();
					g.canvas.ctx.strokeStyle = 'rgb(0,0,0)';
					g.canvas.ctx.lineWidth = g.options.grid.border;
					g.canvas.ctx.strokeRect(g.selectfrom[0]-0.5,g.selectfrom[1]-0.5,g.selectto[0]-g.selectfrom[0],g.selectto[1]-g.selectfrom[1]);
					g.canvas.ctx.stroke();
					g.canvas.ctx.closePath();
				}
			}
			return true;
		}).bind("mouseup",{me:this},function(ev){
			var g = ev.data.me;	 // The graph object
			if(g.selecting){
				var c1 = g.pixel2data(g.selectfrom[0],g.selectfrom[1]);
				var c2 = g.pixel2data(g.selectto[0],g.selectto[1]);
				if(c1.x==c2.x && c1.y==c2.y){
					g.zoom();
				}else{
					xlo = (c1.x < c2.x) ? c1.x : c2.x;
					xhi = (c1.x < c2.x) ? c2.x : c1.x;
					ylo = (c1.y < c2.y) ? c1.y : c2.y;
					yhi = (c1.y < c2.y) ? c2.y : c1.y;
					g.zoom(xlo,xhi,ylo,yhi);
				}
			}
			g.selecting = false;
			g.canvas.pasteFromClipboard();
			g.drawOverlay();
			return true;
		})

		// Extend the options with those provided by the user
		this.setOptions(options);
		this.setColours();

		// Finally, set the data and update the display
		this.updateData(data);

		if(this.logging) console.log("Total:" + (new Date() - d) + "ms");
		return this;
	}
	// Attach a handler to an event for the Graph object in a style similar to that used by jQuery
	//   .bind(eventType[,eventData],handler(eventObject));
	//   .bind("resize",function(e){ console.log(e); });
	//   .bind("resize",{me:this},function(e){ console.log(e.data.me); });
	Graph.prototype.bind = function(ev,e,fn){
		if(typeof ev!="string") return this;
		if(typeof fn=="undefined"){ fn = e; e = {}; }
		else{ e = {data:e} }
		if(typeof e!="object" || typeof fn!="function") return this;
		if(this.events[ev]) this.events[ev].push({e:e,fn:fn});
		else this.events[ev] = [{e:e,fn:fn}];
		return this;
	}
	// Trigger a defined event with arguments. This is for internal-use to be 
	// sure to include the correct arguments for a particular event
	Graph.prototype.trigger = function(ev,args){
		if(typeof ev != "string") return;
		if(typeof args != "object") args = {};
		var o = [];
		if(typeof this.events[ev]=="object"){
			for(var i = 0 ; i < this.events[ev].length ; i++){
				var e = G.extend(this.events[ev][i].e,args);
				if(typeof this.events[ev][i].fn == "function") o.push(this.events[ev][i].fn.call(this,e))
			}
		}
		if(o.length > 0) return o;
	}
	Graph.prototype.setOptions = function(options){
		options = options || {};
		if(typeof this.options!="object") this.options = {};
		// Set the width and height
		this.options.width = parseInt(getStyle(this.id, 'width'), 10);
		this.options.height = parseInt(getStyle(this.id, 'height'), 10);
		// Add user-defined options
		this.options = G.extend(this.options, options);

		// Set defaults for options that haven't already been set
		if(typeof this.options.grid!="object") this.options.grid = {};
		if(typeof this.options.grid.show!="boolean") this.options.grid.show = true;
		if(typeof this.options.grid.border!="number") this.options.grid.border = 1;
		if(typeof this.options.xaxis!="object") this.options.xaxis = {};
		if(typeof this.options.yaxis!="object") this.options.yaxis = {};
		if(typeof this.options.xaxis.label!="string") this.options.xaxis.label = "";
		if(typeof this.options.yaxis.label!="string") this.options.yaxis.label = "";
		if(typeof this.options.xaxis.fit!="boolean") this.options.xaxis.fit = false;
		if(typeof this.options.yaxis.fit!="boolean") this.options.yaxis.fit = false;
		if(typeof this.options.xaxis.log!="boolean") this.options.xaxis.log = false;
		if(typeof this.options.yaxis.log!="boolean") this.options.yaxis.log = false;
		if(typeof this.options.xaxis.mode=="string" && this.options.xaxis.mode=="time") this.options.xaxis.isDate = true;
		return this;
	}
	Graph.prototype.updateData = function(data) {
		this.data = (data.length > 1) ? data : [data];
		this.getGraphRange();
		this.calculateData();
		this.clear();
		this.draw();
	}
	Graph.prototype.setColours = function(){
		this.colours = { background:'', lines:'rgb(0,0,0)', labels:'rgb(0,0,0)' };
		if(typeof this.options.grid.background=="string") this.colours.background = this.options.grid.background;
		if(typeof this.options.grid.color=="string") this.colours.lines = this.options.grid.color;
		if(typeof this.options.labels=="string") this.colours.labels = this.options.grid.color;
	}
	Graph.prototype.getGraphRange = function(){
		this.x = { min: 1e32, max: -1e32, isDate: this.options.xaxis.isDate, log: this.options.xaxis.log, label:{text:this.options.xaxis.label}, fit:this.options.xaxis.fit };
		this.y = { min: 1e32, max: -1e32, log: this.options.yaxis.log, label:{text:this.options.yaxis.label}, fit:this.options.yaxis.fit };

		if(this.data.length <= 0) return this;
		
		//this.errors = (this.options.useerrorsforrange) ? this.data[0].data[0].length - 2 : 0;
		for(var i = 0; i < this.data.length ; i++){
			max = this.data[i].data.length

			if(this.data[0].data[0].err){
				// Need to correct for different +/- errors
				var errs = new Array();
				for(var j = 0; j < max ; j++){
					if(this.data[i].data[j].err) errs.push(this.data[i].data[j].err);
				}
				m = G.stddev(errs);
				var err = (m) ? [m,m] : [0,0];
			}else var err = [0,0];

			for(var j = 0; j < max ; j++){
				if(this.data[i].data[j].x < this.x.min) this.x.min = this.data[i].data[j].x;
				if(this.data[i].data[j].x > this.x.max) this.x.max = this.data[i].data[j].x;
				if(this.data[i].data[j].y-err[1] < this.y.min) this.y.min = this.data[i].data[j].y-err[1];
				if(this.data[i].data[j].y+err[1] > this.y.max) this.y.max = this.data[i].data[j].y+err[1];
			}
			if(typeof this.data[i].hover!="object") this.data[i].hover = {};
		}
		// Keep a record of the data min/max
		this.x.datamin = this.x.min;
		this.x.datamax = this.x.max;
		this.x.datarange = this.x.max-this.x.min;
		this.y.datamin = this.y.min;
		this.y.datamax = this.y.max;
		this.y.datarange = this.y.max-this.y.min;
		this.defineAxis("x");
		this.defineAxis("y");
		return this;
	}

	Graph.prototype.zoom = function(x1,x2,y1,y2){
		// Immediately return if the input seems wrong
		if(typeof x1!="number" || typeof x2!="number" || typeof y1!="number" || typeof y2!="number"){
			this.x.min = this.x.datamin;
			this.x.max = this.x.datamax;
			this.y.min = this.y.datamin;
			this.y.max = this.y.datamax;
			this.defineAxis("x");
			this.defineAxis("y");		
		}else{
			// Re-define the axes
			this.defineAxis("x",x1,x2);
			this.defineAxis("y",y1,y2);
		}
		this.calculateData();
		// Update the graph
		this.clear();
		this.draw();
	}
	
	// For an input data value find the y-pixel location
	Graph.prototype.getYPos = function(y){
		if(this.y.log){
			y = G.log10(y);
			var min = this.y.gmin;
			var max = this.y.gmax;
			var ran = this.y.grange;
		}else{
			var min = this.y.min;
			var max = this.y.max;
			var ran = this.y.range;
		}
		return (y < min || y > max) ? (y > max ? this.chart.top-1 : this.chart.top+this.chart.height+1) : this.options.height-(this.chart.bottom + this.chart.height*((y-min)/ran));
	}
	
	// For an input data value find the x-pixel location
	Graph.prototype.getXPos = function(x){
		if(this.x.log){
			x = G.log10(x);
			var min = this.x.gmin;
			var max = this.x.gmax;
			var ran = this.x.grange;
		}else{
			var min = this.x.min;
			var max = this.x.max;
			var ran = this.x.range;
		}
		return (x < min || x > max) ? (x < min ? this.chart.left-1 : this.chart.left+this.chart.width+1) : (this.x.dir=="reverse" ? this.chart.left + this.chart.width*(Math.abs(max-x)/(ran)) : this.chart.left + this.chart.width*(Math.abs(x-min)/ran));
	}
	
	// For an input data value find the pixel locations
	Graph.prototype.getPixPos = function(x,y){
		return [this.getXPos(x),this.getYPos(y)];
	}
	
	// Are the x,y pixel coordinates in the displayed chart area?
	Graph.prototype.within = function(x,y){
		if(x > this.chart.left && y < this.chart.top+this.chart.height) return true;
		return false;
	}
	
	// Provide the pixel coordinates (x,y) and return the data-space values
	Graph.prototype.pixel2data = function(x,y){
		x = this.x.min+((x-this.chart.left)/this.chart.width)*this.x.range;
		y = this.y.min+(1-(y-this.chart.top)/this.chart.height)*this.y.range;
		return {x:x,y:y};
	}
	
	Graph.prototype.dataAtMousePosition = function(x,y){
		s = "string";
		var found = "";
		// Define a search pattern moving out in pixels
		search = [[0,0],[-1,0],[1,0],[0,-1],[0,1],[1,1],[1,-1],[-1,1],[-1,-1],[-2,0],[0,-2],[2,0],[0,2],[-1,-2],[1,-2],[2,-1],[2,1],[1,2],[-1,2],[-2,1],[-2,-1],[-2,-2],[-2,2],[2,2],[2,-2]];
		for(i = 0; i < search.length; i++){
			dx = x+search[i][0];
			dy = y+search[i][1];
			if(dx >= 0 && dy >= 0 && dx < this.canvas.wide && dy < this.canvas.tall && is(this.lookup[dx][dy],s)) return this.lookup[dx][dy].split(':');
		}
	}
	
	Graph.prototype.highlight = function(d){
		if(this.selecting) return;	// If we are dragging we don't want to highlight points
		if(this.lookup && d && d.length == 2){
			// We want to put the saved version of the canvas back
			this.canvas.pasteFromClipboard();
			this.drawOverlay();

			var s = d[0];
			var i = d[1];
			var data = this.data[s];
			var twopi = 2*Math.PI;
			var rad = (data.points.radius) ? data.points.radius : 1;
			var ii = this.getPixPos(data.data[i].x,data.data[i].y);
			this.canvas.ctx.beginPath();

			this.canvas.ctx.lineWidth = 1.5;
			this.canvas.ctx.strokeStyle = (data.color ? parseColour(data.color) : '#df0000');
			this.canvas.ctx.fillStyle = 'rgba(255,255,255,0.3)';
			this.canvas.ctx.arc(ii[0],ii[1],rad*6,0,twopi,false);
			this.canvas.ctx.fill();
			this.canvas.ctx.stroke();
			this.canvas.ctx.closePath();

			this.canvas.ctx.beginPath();
			this.canvas.ctx.arc(ii[0],ii[1],rad,0,twopi,false);
			this.canvas.ctx.strokeStyle = (data.color ? parseColour(data.color) : '#df0000');
			this.canvas.ctx.stroke();
			this.canvas.ctx.closePath();
			
			if(!this.coordinates){
				this.canvas.container.append('<div class="coordinates" style="position:absolute;background-color:black;color:white;padding:8px;-webkit-border-radius: 5px;-moz-border-radius: 5px;border-radius: 5px;box-shadow: 0px 0px 5px rgba(0,0,0,0.6);-moz-box-shadow: 0px 0px 5px rgba(0,0,0,0.6);-webkit-box-shadow: 0px 0px 5px rgba(0,0,0,0.6);"></div>');
				this.coordinates = this.canvas.container.find('.coordinates');
			}
			this.coordinates.show();
			if(typeof data.css=="object") this.coordinates.css(data.css);
			
			// Build the hovertext output
			val = {
				title: (data.title) ? data.title : "", 
				xlabel: (this.x.label.text ? this.x.label.text : (this.x.isDate ? 'Time' : 'x')),
				ylabel: (this.y.label.text ? this.y.label.text : 'y'),
				data: data.data[i]
			}
			txt = is(data.hover.text,"function") ? data.hover.text.call(this,val) : "";
			if(typeof txt!="string" || txt=="") txt = "{{ xlabel }}: {{ x }}<br />{{ ylabel }}: {{ y }}<br />Uncertainty: {{ err }}";
			var html = (typeof data.hover.text=="string") ? data.hover.text : txt;
			if(typeof data.hover.before=="string") html = data.hover.before+html;
			if(typeof data.hover.after=="string") html = html+data.hover.after;
			html = html.replace(/{{ *x *}}/g,(this.x.isDate ? new Date(val.data.x) : val.data.x));
			html = html.replace(/{{ *y *}}/g,val.data.y);
			html = html.replace(/{{ *xlabel *}}/g,val.xlabel);
			html = html.replace(/{{ *ylabel *}}/g,val.ylabel);
			html = html.replace(/{{ *err *}}/g,(val.data.err ? val.data.err : 0));
			html = html.replace(/{{ *title *}}/g,val.title);
			while(html.match(/{{.*}}/)){
				var a = html.indexOf("{{")+2;
				var b = html.indexOf("}}");
				var pattern = html.substring(a,b);
				pattern = pattern.replace(/^\s+|\s+$/g,"");	// trim
				html = html.replace(new RegExp("{{ *"+pattern+" *}}","g"),(typeof val.data[pattern]=="string") ? val.data[pattern] : "");
			}
			

			this.coordinates.html(html);
			var x = ii[0]-this.coordinates.outerWidth()-1;
			if(x < this.chart.padding) x = ii[0]+1;
			this.coordinates.css({'left':x,'top':ii[1]+1});

			this.annotated = true;
		}else{
			if(this.annotated){
				this.annotated = false;
				this.coordinates.hide();
				//this.clear();
				//this.draw();
				this.canvas.pasteFromClipboard();
				this.drawOverlay();
			}
		}
	}

	// Defines this.x.max, this.x.min, this.x.inc, this.x.range
	Graph.prototype.defineAxis = function(axis,min,max){

		// Immediately return if the input seems wrong
		if(typeof axis != "string" || (axis != "x" && axis != "y")) return false;

		// Set the min/max if provided
		if(typeof max=="number") this[axis].max = max;
		if(typeof min=="number") this[axis].min = min;
		// Set the range of the data
		this[axis].range = this[axis].max - this[axis].min;

		// Sort out what to do for log scales
		if(this[axis].log){
			// Adjust the low and high values for log scale
			this[axis].gmax = Math.ceil(G.log10(this[axis].max));
			this[axis].gmin = (this[axis].min <= 0) ? this[axis].gmax-2 : Math.floor(G.log10(this[axis].min));

			this[axis].inc = 1;
			this[axis].range = this[axis].max-this[axis].min;
			this[axis].grange = this[axis].gmax-this[axis].gmin;
			return true;
		}

		// If we have zero range we need to expand it
		if(this[axis].range < 0){
			this[axis].inc = 0.0;
			this[axis].grange = 0.0;
			return true;
		}else if(this[axis].range == 0){
			this[axis].gmin = Math.ceil(this[axis].max)-1;
			this[axis].gmax = Math.ceil(this[axis].max);
			this[axis].min = this[axis].gmin;
			this[axis].max = this[axis].gmax;
			this[axis].inc = 1.0;
			this[axis].range = this[axis].max-this[axis].min;
			this[axis].grange = this[axis].gmax-this[axis].gmin;
			return true;
		}

		var param = {'name': 'seconds', 'div': 1, 'base': 10};
		var rg = this[axis].range;
		var mx = this[axis].max;
		var mn = this[axis].min;
		var t_inc;
		
		// Calculate reasonable grid line spacings
		if(this[axis].isDate){
			// Dates are in milliseconds
			// Grid line spacings can range from 1 ms to 10000 years
			var steps = [{'name': 'seconds','div':1000,'spacings':[0.001,0.002,0.005,0.01,0.02,0.05,0.1,0.25,0.5,1,2,5,10,15]},
					{'name': 'minutes', 'div':60000,'spacings':[0.5,1,2,5,10,15,20,30]},
					{'name': 'hours', 'div':3600000,'spacings':[0.5,1,2,4,6]},
					{'name': 'days', 'div':86400000,'spacings':[0.5,1,2,7]},
					{'name': 'weeks', 'div':7*86400000,'spacings':[1,2,4,8]},
					{'name': 'years', 'div':31557600000,'spacings':[0.25,0.5,1,2,5,10,20,50,100,200,500,1000,2000,5000]}];
			var t_div;

			for(var s = 0; s < steps.length ; s++){
				for(var sp = 0; sp < steps[s].spacings.length; sp++){
					var n = Math.ceil(this[axis].range/(steps[s].div*steps[s].spacings[sp]));
					if(n < 1) continue;
					if(!t_div || (n > 3 && n < t_div)){
						t_div = n;
						this[axis].spacing = {'name':steps[s].name,'fract':steps[s].spacings[sp]};
						t_inc = (steps[s].div*steps[s].spacings[sp]);
					}
				}
			}
		}else t_inc = Math.pow(param.base,Math.floor(Math.log(rg)/Math.log(param.base)));

		//t_inc = Math.pow(10,Math.ceil(G.log10(this[axis].range/10)));
		var t_max = (Math.floor(mx/t_inc))*t_inc;
		if(t_max < mx) t_max += t_inc;
		var t_min = t_max;
		var i = 0;
		do {
			i++;
			t_min -= t_inc;
		}while(t_min > mn);

		// Test for really tiny values that might mess up the calculation
		if(Math.abs(t_min) < 1E-15) t_min = 0.0;
	
		// Add more tick marks if we only have a few
		while(i < (this[axis].isDate ? 3 : 5)) {
			t_inc /= 2.0;
			if((t_min + t_inc) <= mn) t_min += t_inc;
			if((t_max - t_inc) >= mx) t_max -= t_inc ;
			i = i*2;
		}

		// Set the first/last gridline values as well as the spacing
		this[axis].gmin = t_min;
		this[axis].gmax = t_max;
		this[axis].inc = t_inc;
		this[axis].grange = this[axis].gmax-this[axis].gmin;

		return true;
	}

	Graph.prototype.getChartOffset = function(){
		if(typeof this.chart!="object") this.chart = {}
		var fs = getStyle(this.canvas.id, 'font-size');
		var ff = getStyle(this.canvas.id, 'font-family');
		if(this.canvas.fullscreen){
			this.chart.padding = this.canvas.wide/40;
			this.chart.fontsize = this.canvas.wide/80;
			this.chart.fontfamily = (typeof ff=="string") ? ff : "";
		}else{
			this.chart.padding = 0;
			this.chart.fontsize = (typeof fs=="string") ? parseInt(fs) : 12;
			this.chart.fontfamily = (typeof ff=="string") ? ff : "";
		}
		// Correct for sub-pixel positioning
		b = this.options.grid.border*0.5;
		this.chart.top = this.chart.padding+b;
		this.chart.left = (this.y.label.text) ? this.chart.padding+Math.round(3.5*this.chart.fontsize)-b : this.chart.padding+Math.round(3*this.chart.fontsize)-b;
		this.chart.right = this.chart.padding+b;
		this.chart.bottom = (this.x.label.text) ? this.chart.padding+Math.round(4.5*this.chart.fontsize/2)-b : this.chart.padding+Math.round(2.5*this.chart.fontsize/2)+b;
		this.chart.width = this.canvas.wide-this.chart.right-this.chart.left;
		this.chart.height = this.canvas.tall-this.chart.bottom-this.chart.top;
		return this;
	}
	
	// Draw the axes and grid lines for the graph
	Graph.prototype.drawAxes = function(){
		grid = this.options.grid.show;
		o = this.chart;
		rot = Math.PI/2;
		
		this.canvas.ctx.beginPath();
		this.canvas.ctx.font = this.chart.fontsize+'px '+this.chart.fontfamily;
		this.canvas.ctx.textBaseline = 'middle';

		// Draw main rectangle
		this.canvas.ctx.strokeStyle = 'rgb(0,0,0)';
		this.canvas.ctx.lineWidth = this.options.grid.border;
		if(typeof this.options.grid.background=="string"){
			this.canvas.ctx.fillStyle = this.options.grid.background;
			this.canvas.ctx.fillRect(o.left,o.top,o.width,o.height);
		}
		this.canvas.ctx.strokeRect(o.left,o.top,o.width,o.height);

		this.canvas.ctx.lineWidth = 1;
		// Draw x label
		if(this.x.label.text!=""){
			this.canvas.ctx.textAlign = "center";
			this.canvas.ctx.fillStyle = (this.x.label.color ? this.x.label.color : "black");
			this.canvas.ctx.fillText(this.x.label.text,o.left+o.width/2, this.options.height-Math.round(this.chart.fontsize/2)-this.chart.padding);
		}

		if(this.y.label.text!=""){
			this.canvas.ctx.textAlign = "center";
			this.canvas.ctx.fillStyle = (this.x.label.color ? this.x.label.color : "black");
			this.canvas.ctx.rotate(-rot);
			this.canvas.ctx.fillText(this.y.label.text,-(o.top+(o.height/2)),Math.round(this.chart.fontsize/2)+this.chart.padding);
			this.canvas.ctx.rotate(rot);
		}
		this.canvas.ctx.closePath();

		if(!this.subgrid){
			v = [2,3,4,5,6,7,8,9]
			this.subgrid = []
			for(var i = 0 ; i < v.length ; i++){
				this.subgrid[i] = G.log10(v[i]);
			}
		}

		this.canvas.ctx.lineWidth = (this.options.grid.width ? this.options.grid.width : 0.5);

		// Draw y-axis grid and labels
		this.canvas.ctx.textAlign = "end";
		x1 = this.chart.left;
		x2 = this.chart.left+this.chart.width;
		// Calculate the number of decimal places for the increment - helps with rounding errors
		prec = ""+this.y.inc;
		prec = prec.length-prec.indexOf('.')-1;
		fshalf = Math.ceil(this.chart.fontsize/2);
		for(var i = this.y.gmin; i <= this.y.gmax; i += this.y.inc) {
			y = this.getYPos((this.y.log ? Math.pow(10, i) : i));
			if(!y || y < this.chart.top || y > this.chart.top+this.chart.height) continue;
			// As <canvas> usings sub-pixel positioning we want to shift the placement 0.5 pixels
			y = (y-Math.round(y) > 0) ? Math.floor(y)+0.5 : Math.ceil(y)-0.5;
			j = (this.y.log) ? i : i.toFixed(prec);
			a = (j==this.y.gmax) ? fshalf : (j==this.y.gmin ? -fshalf : 0);
			this.canvas.ctx.beginPath();
			this.canvas.ctx.strokeStyle = (this.options.grid.color ? this.options.grid.color : 'rgba(0,0,0,0.5)');
			this.canvas.ctx.fillStyle = (this.y.label.color ? this.y.label.color : "black");
			this.canvas.ctx.fillText((this.y.log ? Math.pow(10, j) : j),x1-3,(y+a).toFixed(1));
			if(grid && i != this.y.gmin && i != this.y.gmax){
				this.canvas.ctx.moveTo(x1,y);
				this.canvas.ctx.lineTo(x2,y);
			}
			this.canvas.ctx.stroke();
			this.canvas.ctx.closePath();
			if(grid && this.y.log){
				this.canvas.ctx.beginPath();
				s = (this.options.grid.sub) ? this.options.grid.sub : {};
				this.canvas.ctx.strokeStyle = (s.color ? s.color : 'rgba(0,0,0,0.2)');
				this.canvas.ctx.lineWidth = (s.width ? s.width : 0.5);
				for(var j = 0; j < this.subgrid.length ; j++){
					di = i+this.subgrid[j];
					if(di < this.y.gmax){
						y = this.getYPos(Math.pow(10,di))+0.5;
						// As <canvas> usings sub-pixel positioning we want to shift the placement 0.5 pixels
						y = (y-Math.round(y) > 0) ? Math.floor(y)+0.5 : Math.ceil(y)-0.5;
						this.canvas.ctx.moveTo(x1,y);
						this.canvas.ctx.lineTo(x2,y);
					}
				}
				this.canvas.ctx.stroke();
				this.canvas.ctx.closePath();
			}
		}
		this.canvas.ctx.closePath();

		// Draw x-axis grid and labels
		this.canvas.ctx.textBaseline = 'top';
		y1 = this.chart.top+this.chart.height;
		y2 = this.chart.top;
		// Calculate the number of decimal places for the increment - helps with rounding errors
		prec = ""+this.x.inc;
		prec = (prec.indexOf('.') > 0) ? prec.length-prec.indexOf('.')-1 : 0;
		for(var i = this.x.gmin; i <= this.x.gmax; i += this.x.inc) {
			x = this.getXPos((this.x.log ? Math.pow(10,i): i));
			if(!x || x < this.chart.left || x > this.chart.left+this.chart.width) continue;
			// As <canvas> usings sub-pixel positioning we want to shift the placement 0.5 pixels
			x = (x-Math.round(x) > 0) ? Math.floor(x)+0.5 : Math.ceil(x)-0.5;
			j = (this.y.log) ? i : i.toFixed(prec);
			this.canvas.ctx.beginPath();
			this.canvas.ctx.textAlign = (j==this.x.gmax) ? 'end' : (j==this.x.gmin ? 'start' : 'center');
			this.canvas.ctx.strokeStyle = (this.options.grid.color ? this.options.grid.color : 'rgba(0,0,0,0.5)');
			var str = (this.x.isDate) ? this.formatLabelDate(j) : addCommas((this.x.log ? Math.pow(10, j) : j))
			var ds = str.split(/\n/);
			this.canvas.ctx.fillStyle = (this.x.label.color ? this.x.label.color : "black");
			for(var d = 0; d < ds.length ; d++) this.canvas.ctx.fillText(ds[d],x.toFixed(1),(y1+3+d*this.chart.fontsize).toFixed(1));
			if(grid && j != this.x.gmin && j != this.x.gmax){
				this.canvas.ctx.moveTo(x,y1);
				this.canvas.ctx.lineTo(x,y2);
				this.canvas.ctx.stroke();
			}
			this.canvas.ctx.closePath();
			if(grid && this.x.log){
				this.canvas.ctx.beginPath();
				s = (this.options.grid.sub) ? this.options.grid.sub : {};
				this.canvas.ctx.strokeStyle = (s.color ? s.color : 'rgba(0,0,0,0.2)');
				for(var j = 0; j < this.subgrid.length ; j++){
					di = i+this.subgrid[j];
					if(di < this.x.gmax){
						x = this.getXPos(Math.pow(10,di));
						// As <canvas> usings sub-pixel positioning we want to shift the placement 0.5 pixels
						x = (x-Math.round(x) > 0) ? Math.floor(x)+0.5 : Math.ceil(x)-0.5;
						this.canvas.ctx.moveTo(x,this.chart.top);
						this.canvas.ctx.lineTo(x,y1);
					}
				}
				this.canvas.ctx.stroke();
				this.canvas.ctx.closePath();
			}
		}
		return this;
	}

	Graph.prototype.formatLabelDate = function(d){
		d = new Date(parseInt(d));
		var hr = zeroFill(d.getUTCHours(),2);
		var mn = zeroFill(d.getUTCMinutes(),2);
		var sc = zeroFill(d.getUTCSeconds()+d.getUTCMilliseconds()/1000,2);
		var dy = zeroFill(d.getUTCDate(),2);
		var mo = zeroFill(d.getUTCMonth()+1,2);
		var yr = d.getUTCFullYear();
		var n = this.x.spacing.name;
		if(n=="seconds") return (this.x.spacing.fract >= 1 ? hr+":"+mn+":"+sc : ""+sc);
		else if(n=="minutes") return hr+":"+mn+(d.getUTCSeconds()==0 ? "" : ":"+sc);
		else if(n=="hours") return hr+":"+mn;
		else if(n=="days") return (this.x.spacing.fract >= 1 ? yr+"/"+mo+"/"+dy : yr+"/"+mo+"/"+dy+' '+hr+':'+mn);
		else if(n=="weeks") return yr+"/"+mo+"/"+dy+(hr=="00" ? '' : ' '+Math.round((d.getUTCHours()+(d.getUTCMinutes()/60)))+'h');
		else if(n=="years") return ((this.x.spacing.fract >= 1) ? ""+(d.getUTCFullYear()+Math.round((d.getUTCMonth()+1)/12)) : (Math.round(d.getUTCMonth()+1)==12 ? (d.getUTCFullYear()+1)+"/01/01" : d.getUTCFullYear()+'/'+mo+'/01'));
		else return hr+":"+mn+":"+sc;
	}

	// Function to calculate the x,y coordinates for each data point. 
	// It also creates a pixel-based lookup table for mouse hover events
	Graph.prototype.calculateData = function(){
		this.getChartOffset();

		// Define a pixel-based lookup table
		this.lookup = new Array(this.canvas.wide);
		for (i=0; i < this.canvas.wide; i++){
			this.lookup[i] = new Array(this.canvas.tall);
		}

		for(var s = 0; s < this.data.length ; s++){
			l = this.data[s].data.length
			this.data[s].x = new Array(l);
			this.data[s].y = new Array(l);
			for(var i = 0; i < l ; i++){
				ii = this.getPixPos(this.data[s].data[i].x,this.data[s].data[i].y);
				x = Math.round(ii[0]);
				y = Math.round(ii[1]);
				if(this.data[s].hoverable && typeof ii[0]=="number" && typeof ii[1]=="number" && x < this.lookup.length && y < this.lookup[x].length && this.data[s].data[i].x >= this.x.min && this.data[s].data[i].x <= this.x.max && this.data[s].data[i].y >= this.y.min && this.data[s].data[i].y <= this.y.max) this.lookup[x][y] = s+":"+i;
				this.data[s].x[i] = ii[0];
				this.data[s].y[i] = ii[1];
			}
		}
		return this;
	}

	// Draw the data onto the graph
	Graph.prototype.drawData = function(){

		var lo,hi,x,y,ii,l;
		var twopi = Math.PI*2;

		for(var s = 0; s < this.data.length ; s++){

			this.canvas.ctx.strokeStyle = (this.data[s].color ? parseColour(this.data[s].color) : '#df0000');

			// Draw lines
			if(this.data[s].lines.show){
				this.canvas.ctx.beginPath();
				this.canvas.ctx.lineWidth = (this.data[s].lines.width ? this.data[s].lines.width : 1);
				for(var i = 0; i < this.data[s].x.length ; i++){
					if(this.data[s].x[i] && this.data[s].y[i]){
						if(this.data[s].data[i].x >= this.x.min && this.data[s].data[i].x <= this.x.max && this.data[s].data[i].y >= this.y.min && this.data[s].data[i].y <= this.y.max){
							if(i == 0) this.canvas.ctx.moveTo(this.data[s].x[i],this.data[s].y[i]);
							else this.canvas.ctx.lineTo(this.data[s].x[i],this.data[s].y[i]);
						}else{
							this.canvas.ctx.moveTo(this.data[s].x[i],this.data[s].y[i]);
						}
					}
				}
				this.canvas.ctx.stroke();
				this.canvas.ctx.closePath();
			}
		
			if(typeof this.data[s].points=="undefined") this.data[s].points = { show: true };
			var rad = (this.data[s].points.radius) ? this.data[s].points.radius : 1;

			if(this.data[s].points.show){
				this.canvas.ctx.fillStyle = (this.data[s].color ? parseColour(this.data[s].color) : '#df0000');
				this.canvas.ctx.lineWidth = (0.8);
				for(var i = 0; i < this.data[s].x.length ; i++){
					if(this.data[s].x[i] && this.data[s].y[i] && this.data[s].data[i].x >= this.x.min && this.data[s].data[i].x <= this.x.max && this.data[s].data[i].y >= this.y.min && this.data[s].data[i].y <= this.y.max){
						if(this.data[s].y[i] < this.chart.top+this.chart.height){
							this.canvas.ctx.moveTo(this.data[s].x[i],this.data[s].y[i]);
							this.canvas.ctx.beginPath();
							this.canvas.ctx.arc(this.data[s].x[i],this.data[s].y[i],rad,0,twopi,false);
							this.canvas.ctx.stroke();
							e = (this.data[s].data[i].err) ? (this.data[s].data[i].err.length==2 ? 2 : 1) : 0;
							if(e > 0){
								if(e == 2){
									hi = this.getYPos(this.data[s].data[i].y+this.data[s].data[i].err[0]);
									lo = this.getYPos(this.data[s].data[i].y-this.data[s].data[i].err[1]);
								}else{
									hi = this.getYPos(this.data[s].data[i].y+this.data[s].data[i].err);
									lo = this.getYPos(this.data[s].data[i].y-this.data[s].data[i].err);
								}
								
								if(hi && lo){
									this.canvas.ctx.beginPath();
									this.canvas.ctx.moveTo(this.data[s].x[i],lo);
									this.canvas.ctx.lineTo(this.data[s].x[i],hi);
									this.canvas.ctx.stroke();
									this.canvas.ctx.closePath();
								}
							}
						}
					}
				}
			}
		}
		return this;
	}
	Graph.prototype.addLine = function(opt){
		// Should sanitize the input here
		this.lines.push(opt);
		return this;
	}
	Graph.prototype.removeLines = function(opt){
		this.lines = [];
		return this;
	}
	Graph.prototype.drawLines = function(){
		// Loop over each line
		for(var l = 0; l < this.lines.length ; l++){
			if(this.lines[l].x){
				x = (this.lines[l].x.length == 2) ? this.lines[l].x : [this.lines[l].x,this.lines[l].x];
				x1 = this.getXPos((this.x.log ? Math.pow(10,x[0]): x[0]));
				x2 = this.getXPos((this.x.log ? Math.pow(10,x[1]): x[1]));
			}else{
				x1 = this.chart.left;
				x2 = this.chart.left+this.chart.width;
			}
			if(this.lines[l].y){
				y = (this.lines[l].y.length == 2) ? this.lines[l].y : [this.lines[l].y,this.lines[l].y];
				y1 = this.getYPos((this.y.log ? Math.pow(10,y[0]): y[0]));
				y2 = this.getYPos((this.y.log ? Math.pow(10,y[1]): y[1]));
			}else{
				y1 = this.chart.top+this.chart.height;
				y2 = this.chart.top;
			}
			this.canvas.ctx.beginPath();
			this.canvas.ctx.strokeStyle = (typeof this.lines[l].color=="string" ? this.lines[l].color : 'black');
			this.canvas.ctx.lineWidth = (typeof this.lines[l].width=="number" ? this.lines[l].width : 1);
			this.canvas.ctx.moveTo(x1,y1);
			this.canvas.ctx.lineTo(x2,y2);
			this.canvas.ctx.stroke();
			this.canvas.ctx.closePath();
		}
		return this;
	}
	// Clear the canvas
	Graph.prototype.clear = function(){
		this.canvas.ctx.clearRect(0,0,this.canvas.wide,this.canvas.tall);
		return this;
	}
	
	// Draw everything
	Graph.prototype.draw = function(){
		this.drawAxes();
		this.drawData();
		this.canvas.copyToClipboard();
		this.drawOverlay();
		return this;
	}
	Graph.prototype.drawOverlay = function(){
		this.drawLines();
		return this;
	}

	$.graph = function(element, data, options) {
		return new Graph(element, data, options);
	};

})(jQuery);
