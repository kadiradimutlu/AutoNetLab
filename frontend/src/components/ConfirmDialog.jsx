import { useEffect } from "react";
import { createRoot } from "react-dom/client";

function ConfirmDialog({
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onCancel,
  onConfirm
}) {
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        onCancel();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onCancel]);

  return (
    <div
      className="confirm-dialog-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onCancel();
        }
      }}
      role="presentation"
    >
      <section
        aria-labelledby="confirm-dialog-title"
        aria-modal="true"
        className="confirm-dialog"
        role="dialog"
      >
        <div className="confirm-dialog-content">
          <h3 id="confirm-dialog-title">{title}</h3>
          <p>{message}</p>
        </div>

        <div className="confirm-dialog-actions">
          <button
            className="secondary-button confirm-dialog-button"
            onClick={onCancel}
            type="button"
          >
            {cancelLabel}
          </button>

          <button
            className={`${variant === "destructive" ? "danger-button" : "primary-button"} confirm-dialog-button`}
            onClick={onConfirm}
            type="button"
          >
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}

export function confirmAction(options) {
  if (typeof document === "undefined") {
    return Promise.resolve(true);
  }

  return new Promise((resolve) => {
    const container = document.createElement("div");
    container.className = "confirm-dialog-mount";
    document.body.appendChild(container);

    const root = createRoot(container);
    let isResolved = false;

    function cleanup(result) {
      if (isResolved) {
        return;
      }

      isResolved = true;
      root.unmount();
      container.remove();
      resolve(result);
    }

    root.render(
      <ConfirmDialog
        {...options}
        onCancel={() => cleanup(false)}
        onConfirm={() => cleanup(true)}
      />
    );
  });
}

export default ConfirmDialog;
