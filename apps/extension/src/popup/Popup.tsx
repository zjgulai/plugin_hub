import { createRoot } from "react-dom/client";

export function Popup() {
  return (
    <main aria-label="Plugin Hub VOC Collector">
      <header>
        <h1>Plugin Hub</h1>
      </header>
      <section aria-labelledby="collection-title">
        <h2 id="collection-title">VOC Capture</h2>
        <button type="button">Upload Collection</button>
      </section>
    </main>
  );
}

const rootElement = document.getElementById("root");

if (rootElement) {
  createRoot(rootElement).render(<Popup />);
}
