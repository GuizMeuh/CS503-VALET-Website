window.HELP_IMPROVE_VIDEOJS = false;

// ── Sokoban interactive GIF picker ────────────────────────────────────────────
var SOKOBAN_CAPTIONS = {
  baseline:      'Baseline PPO agent — no oracle access.',
  oracle_free:   'Free oracle (cost=0, acc=100%): agent queries nearly every step and solves consistently.',
  oracle_cost01: 'Cost=0.1: agent queries heavily but begins to self-regulate.',
  oracle_cost05: 'Cost=0.5: agent queries selectively — only at critical decision points.',
  oracle_cost08: 'Cost=0.8: agent queries rarely, relying mostly on its own learned policy.',
  oracle_linear: 'Linear cost schedule (0→2 over 2M steps): agent bootstraps on cheap guidance early, then internalizes the policy as querying becomes expensive.',
};

function setSokobanGif(key, btn) {
  document.querySelectorAll('#sokoban-buttons .button').forEach(function(b) {
    b.classList.remove('is-dark');
  });
  btn.classList.add('is-dark');
  // Cache-bust so the GIF restarts from frame 1
  document.getElementById('sokoban-demo').src =
    './static/gifs/sokoban/' + key + '.gif?t=' + Date.now();
  document.getElementById('sokoban-caption').textContent = SOKOBAN_CAPTIONS[key];
}
// ─────────────────────────────────────────────────────────────────────────────

var INTERP_BASE = "./static/interpolation/stacked";
var NUM_INTERP_FRAMES = 240;

var interp_images = [];
function preloadInterpolationImages() {
  for (var i = 0; i < NUM_INTERP_FRAMES; i++) {
    var path = INTERP_BASE + '/' + String(i).padStart(6, '0') + '.jpg';
    interp_images[i] = new Image();
    interp_images[i].src = path;
  }
}

function setInterpolationImage(i) {
  var image = interp_images[i];
  image.ondragstart = function() { return false; };
  image.oncontextmenu = function() { return false; };
  $('#interpolation-image-wrapper').empty().append(image);
}


$(document).ready(function() {
    var options = {
			slidesToScroll: 1,
			slidesToShow: 3,
			loop: true,
			infinite: true,
			autoplay: false,
			autoplaySpeed: 3000,
    }

		// Initialize all div with carousel class
    var carousels = bulmaCarousel.attach('.carousel', options);

    // Loop on each carousel initialized
    for(var i = 0; i < carousels.length; i++) {
    	// Add listener to  event
    	carousels[i].on('before:show', state => {
    		console.log(state);
    	});
    }

    // Access to bulmaCarousel instance of an element
    var element = document.querySelector('#my-element');
    if (element && element.bulmaCarousel) {
    	// bulmaCarousel instance is available as element.bulmaCarousel
    	element.bulmaCarousel.on('before-show', function(state) {
    		console.log(state);
    	});
    }

    /*var player = document.getElementById('interpolation-video');
    player.addEventListener('loadedmetadata', function() {
      $('#interpolation-slider').on('input', function(event) {
        console.log(this.value, player.duration);
        player.currentTime = player.duration / 100 * this.value;
      })
    }, false);*/
    preloadInterpolationImages();

    $('#interpolation-slider').on('input', function(event) {
      setInterpolationImage(this.value);
    });
    setInterpolationImage(0);
    $('#interpolation-slider').prop('max', NUM_INTERP_FRAMES - 1);

    bulmaSlider.attach();

})
