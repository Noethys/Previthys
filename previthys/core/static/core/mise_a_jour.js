/*
 * -*- coding: utf-8 -*-
 * Copyright (c) 2026 Ivan LUCAS.
 * Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
 * Distribué sous licence GNU GPL.
 */

/* Empêche un double envoi et affiche un état d'attente pendant l'installation (peut prendre plusieurs dizaines de secondes). */
document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("form_mise_a_jour");
  if (!form) return;
  form.addEventListener("submit", function () {
    var bouton = form.querySelector("button[type=submit]");
    bouton.disabled = true;
    bouton.textContent = "Installation en cours, veuillez patienter...";
  });
});
