/*
 * -*- coding: utf-8 -*-
 * Copyright (c) 2026 Ivan LUCAS.
 * Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
 * Distribué sous licence GNU GPL.
 */

/* Formulaire d'une action : portée (générale ou liée à des risques), choix des risques par unité. */
(function () {
  var formulaire = document.getElementById("formulaire-action");
  if (!formulaire) return;
  var blocRisques = document.getElementById("bloc-risques");
  var blocStructure = document.getElementById("bloc-structure");
  var compteur = document.getElementById("compteur-risques");
  var cases = Array.prototype.slice.call(formulaire.querySelectorAll('input[name="risques"]'));

  function portee() {
    var coche = formulaire.querySelector('input[name="portee"]:checked');
    return coche ? coche.value : "risques";
  }

  function majPortee() {
    var generale = portee() === "generale";
    if (blocRisques) blocRisques.hidden = generale;
    if (blocStructure) blocStructure.hidden = !generale;
  }

  function majCompteur() {
    if (!compteur) return;
    var cochees = cases.filter(function (c) { return c.checked; });
    var unites = {};
    cochees.forEach(function (c) { unites[c.getAttribute("data-unite")] = true; });
    var n = cochees.length, u = Object.keys(unites).length;
    compteur.textContent = n === 0 ? "Aucun risque coché." :
      n + " risque" + (n > 1 ? "s" : "") + " coché" + (n > 1 ? "s" : "") + " dans " + u + " unité" + (u > 1 ? "s" : "") + "." +
      (u > 1 ? " L'action sera commune à ces unités." : "");
  }

  formulaire.addEventListener("change", function (e) {
    if (e.target.name === "portee") majPortee();
    if (e.target.name === "risques") majCompteur();
  });

  var boutonCocher = document.getElementById("bouton-cocher");
  if (boutonCocher) {
    boutonCocher.addEventListener("click", function () {
      var categorie = document.getElementById("cocher-categorie").value;
      cases.forEach(function (c) { if (c.getAttribute("data-categorie") === categorie) c.checked = true; });
      majCompteur();
    });
    document.getElementById("bouton-decocher").addEventListener("click", function () {
      cases.forEach(function (c) { c.checked = false; });
      majCompteur();
    });
  }

  var filtre = document.getElementById("filtre-risques");
  if (filtre) {
    filtre.addEventListener("input", function () {
      var texte = filtre.value.trim().toLowerCase();
      formulaire.querySelectorAll(".liste-risques .groupe").forEach(function (groupe) {
        var uniteCorrespond = groupe.getAttribute("data-unite").indexOf(texte) !== -1;
        var visibles = 0;
        groupe.querySelectorAll("label").forEach(function (label) {
          var ok = !texte || uniteCorrespond || label.getAttribute("data-texte").indexOf(texte) !== -1;
          label.hidden = !ok;
          if (ok) visibles++;
        });
        groupe.hidden = visibles === 0;
      });
    });
  }

  majPortee();
  majCompteur();
})();
