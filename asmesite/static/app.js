// Open and close event dialogs. Without JS the page still reads fine.
document.addEventListener("click", (event) => {
  const card = event.target.closest("[data-dialog]");
  if (card) {
    const dialog = document.getElementById(card.dataset.dialog);
    if (dialog && dialog.showModal) dialog.showModal();
    return;
  }
  if (event.target.closest("[data-close]")) {
    event.target.closest("dialog").close();
    return;
  }
  // A click on the dialog element itself (not its contents) is a backdrop click.
  if (event.target instanceof HTMLDialogElement) event.target.close();
});
