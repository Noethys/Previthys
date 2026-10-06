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

/* Filtres en liste déroulante des listes (ex. unité de travail) : appliqués dès que la valeur change à la souris.
   Au clavier, les flèches changent la valeur sans recharger la page : l'envoi n'a lieu qu'à la validation (Entrée) ou
   quand on quitte la liste, pour ne pas provoquer de changement de contexte inattendu (RGAA 7.4). */
(function () {
  var clavier = false;
  document.addEventListener("keydown", function (e) {
    var liste = e.target.closest && e.target.closest("select[data-soumettre]");
    if (!liste) return;
    if (e.key === "Enter") {
      e.preventDefault();
      if (liste.dataset.modifie) liste.form.submit();
      return;
    }
    clavier = true;
  });
  document.addEventListener("change", function (e) {
    var liste = e.target;
    if (!liste.matches("select[data-soumettre]")) return;
    if (clavier) { liste.dataset.modifie = "1"; return; }
    liste.form.submit();
  });
  document.addEventListener("focusout", function (e) {
    var liste = e.target;
    if (liste.matches && liste.matches("select[data-soumettre]") && liste.dataset.modifie) liste.form.submit();
    clavier = false;
  });
  document.addEventListener("mousedown", function () { clavier = false; });
})();

/* Formulaire en erreur : le récapitulatif des erreurs reçoit le focus pour être lu en premier (RGAA 11.10). */
document.addEventListener("DOMContentLoaded", function () {
  var recapitulatif = document.getElementById("erreurs-formulaire");
  if (recapitulatif) {
    recapitulatif.focus();
    return;
  }
});

/* Infobulles Bootstrap (ex. texte complet d'une action tronquée dans la liste des risques) : créées au premier survol,
   ce qui fonctionne aussi pour les lignes affichées plus tard par la pagination des listes. */
document.addEventListener("mouseover", function (e) {
  var element = e.target.closest && e.target.closest('[data-bs-toggle="tooltip"]');
  if (!element || !window.bootstrap || bootstrap.Tooltip.getInstance(element)) return;
  bootstrap.Tooltip.getOrCreateInstance(element, {container: "body"}).show();
});

/* Liens d'évitement : le focus est réellement déplacé sur la zone ciblée (utile pour certains navigateurs). */
document.addEventListener("click", function (e) {
  var lien = e.target.closest(".liens-evitement a");
  if (!lien) return;
  var cible = document.querySelector(lien.getAttribute("href"));
  if (cible) { cible.focus(); }
});
