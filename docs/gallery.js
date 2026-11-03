(() => {
  const sections = [...document.querySelectorAll(".figure-section")];
  const previousButton = document.querySelector("#previous-figure");
  const nextButton = document.querySelector("#next-figure");
  const indicator = document.querySelector("#figure-indicator");
  const lightbox = document.querySelector("#lightbox");
  const lightboxImage = lightbox.querySelector("img");
  const closeButton = lightbox.querySelector(".lightbox-close");
  const lightboxPrevious = lightbox.querySelector(".lightbox-previous");
  const lightboxNext = lightbox.querySelector(".lightbox-next");
  const imageTriggers = [...document.querySelectorAll("[data-image]")];
  let activeSection = 0;
  let activeImage = 0;

  const formatIndex = (index, total) =>
    `${String(index + 1).padStart(2, "0")} / ${String(total).padStart(2, "0")}`;

  const updateControls = () => {
    indicator.textContent = formatIndex(activeSection, sections.length);
    previousButton.disabled = activeSection === 0;
    nextButton.disabled = activeSection === sections.length - 1;
  };

  const goToSection = (index) => {
    activeSection = Math.max(0, Math.min(index, sections.length - 1));
    sections[activeSection].scrollIntoView({ behavior: "smooth", block: "start" });
    updateControls();
  };

  const showImage = (index) => {
    activeImage = (index + imageTriggers.length) % imageTriggers.length;
    const trigger = imageTriggers[activeImage];
    lightboxImage.src = trigger.dataset.image;
    lightboxImage.alt = trigger.dataset.alt || "";
  };

  imageTriggers.forEach((trigger, index) => {
    trigger.addEventListener("click", () => {
      showImage(index);
      lightbox.showModal();
    });
  });

  previousButton.addEventListener("click", () => goToSection(activeSection - 1));
  nextButton.addEventListener("click", () => goToSection(activeSection + 1));
  closeButton.addEventListener("click", () => lightbox.close());
  lightboxPrevious.addEventListener("click", () => showImage(activeImage - 1));
  lightboxNext.addEventListener("click", () => showImage(activeImage + 1));
  lightbox.addEventListener("click", (event) => {
    if (event.target === lightbox) lightbox.close();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") {
      lightbox.open ? showImage(activeImage - 1) : goToSection(activeSection - 1);
    }
    if (event.key === "ArrowRight") {
      lightbox.open ? showImage(activeImage + 1) : goToSection(activeSection + 1);
    }
  });

  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    activeSection = Number(visible.target.dataset.galleryIndex);
    updateControls();
  }, { rootMargin: "-25% 0px -45% 0px", threshold: [0.1, 0.35, 0.65] });

  sections.forEach((section) => observer.observe(section));
  updateControls();
})();
