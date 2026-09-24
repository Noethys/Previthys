/*
 * -*- coding: utf-8 -*-
 * Copyright (c) 2026 Ivan LUCAS.
 * Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
 * Distribué sous licence GNU GPL.
 */

/* Comportements communs. Pas de JavaScript en ligne dans les pages (politique CSP « script-src 'self' »). */
document.addEventListener("click", function (e) {
  if (e.target.closest("[data-imprimer]")) {
    window.print();
  }
});

/* Confirmation avant une action irréversible (ex. suppression d'une pièce jointe), sans gestionnaire en ligne. */
document.addEventListener("submit", function (e) {
  var message = e.target.getAttribute("data-confirmer");
  if (message && !window.confirm(message)) {
    e.preventDefault();
  }
});

/* Aperçu d'une pièce jointe image : remplit la fenêtre modale avec l'image et le nom cliqués (motif Bootstrap standard). */
document.addEventListener("show.bs.modal", function (e) {
  if (e.target.id !== "pj-apercu") return;
  var bouton = e.relatedTarget;
  if (!bouton) return;
  var src = bouton.getAttribute("data-pj-src"), nom = bouton.getAttribute("data-pj-nom");
  e.target.querySelector(".modal-body img").src = src;
  e.target.querySelector(".modal-body img").alt = nom;
  e.target.querySelector(".modal-title").textContent = nom;
});
