const slider = document.querySelector(".hero-swiper");
const hero = document.querySelector("[data-hero]");
const ambient = document.querySelector("[data-hero-ambient]");

const applyDominantColor = (swiper) => {
  const activeSlide = swiper.slides[swiper.activeIndex];

  if (!activeSlide) return;

  const color = activeSlide.dataset.color;
  if (hero && color) {
    hero.style.setProperty("--hero-bg", color);
  }

  const image = activeSlide.querySelector("img");
  if (ambient && image) {
    ambient.style.backgroundImage = `url("${image.currentSrc || image.src}")`;
  }
};

if (slider && window.Swiper) {
  new window.Swiper(slider, {
    loop: true,
    speed: 700,
    autoplay: {
      delay: 5000,
      disableOnInteraction: false,
      pauseOnMouseEnter: true,
    },
    pagination: {
      el: ".swiper-pagination",
      clickable: true,
    },
    navigation: {
      nextEl: ".swiper-button-next",
      prevEl: ".swiper-button-prev",
    },
    keyboard: { enabled: true },
    a11y: {
      prevSlideMessage: "Slide anterior",
      nextSlideMessage: "Slide siguiente",
    },
    on: {
      init: applyDominantColor,
      slideChange: applyDominantColor,
    },
  });
}
