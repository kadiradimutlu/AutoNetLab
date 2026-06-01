import { useEffect, useState } from "react";

const SCROLL_THRESHOLD = 300;

function BackToTopButton() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    function handleScroll() {
      setIsVisible(window.scrollY > SCROLL_THRESHOLD);
    }

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  function handleBackToTop() {
    window.scrollTo({
      top: 0,
      behavior: "smooth"
    });
  }

  if (!isVisible) {
    return null;
  }

  return (
    <button
      aria-label="Back to top"
      className="back-to-top-button"
      onClick={handleBackToTop}
      title="Back to top"
      type="button"
    >
      ↑
    </button>
  );
}

export default BackToTopButton;
