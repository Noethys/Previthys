/*
 * -*- coding: utf-8 -*-
 * Copyright (c) 2026 Ivan LUCAS.
 * Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
 * Distribué sous licence GNU GPL.
 */

/* Initialisation des listes DataTables.
   Le tri, le nombre de lignes et les colonnes masquées sont mémorisés par liste dans le navigateur.
   Tant que l'utilisateur n'a pas choisi ses colonnes, celles marquées « masquee-par-defaut » sont masquées. */
(function ($) {
  var LANGUE = {
    buttons: {colvis: "Colonnes", excel: "Excel", copy: "Copier", pageLength: {"-1": "Tout afficher", _: "Afficher %d lignes"}},
    processing: "Traitement en cours...",
    // Le champ de recherche a un libellé (masqué visuellement) en plus de son texte indicatif (RGAA 11.1)
    search: '<span class="visually-hidden">Rechercher dans la liste</span>', searchPlaceholder: "Rechercher",
    lengthMenu: "Afficher _MENU_ éléments",
    info: "Affichage de l'élément _START_ à _END_ sur _TOTAL_ éléments",
    infoEmpty: "Affichage de l'élément 0 à 0 sur 0 éléments",
    infoFiltered: "(filtré de _MAX_ éléments au total)",
    loadingRecords: "Chargement en cours...", zeroRecords: "Aucun élément à afficher", emptyTable: "Aucune donnée",
    paginate: {first: "Premier", previous: "Précédent", next: "Suivant", last: "Dernier"},
    aria: {sortAscending: ": activer pour trier la colonne par ordre croissant", sortDescending: ": activer pour trier la colonne par ordre décroissant"}
  };

  // Exports (Excel, impression) : texte complet des cellules, sans les versions tronquées réservées à l'écran
  var FORMAT_EXPORT = {body: function (donnees) {
    if (typeof donnees !== "string" || donnees.indexOf("<") === -1) return donnees;
    var div = document.createElement("div");
    div.innerHTML = donnees;
    div.querySelectorAll('[aria-hidden="true"]').forEach(function (n) { n.remove(); });
    var lignes = div.querySelectorAll("li");   // une action par ligne
    if (lignes.length) return Array.prototype.map.call(lignes, function (li) { return li.textContent.replace(/\s+/g, " ").trim(); }).join("\n");
    return div.textContent.replace(/\s+/g, " ").trim();
  }};

  function lire(cle) { try { return JSON.parse(localStorage.getItem(cle)) || {}; } catch (e) { return {}; } }
  function ecrire(cle, valeurs) { try { localStorage.setItem(cle, JSON.stringify(valeurs)); } catch (e) {} }

  $(function () {
    $("table.datatable").each(function () {
      var table = this, cle = "core:liste:" + table.dataset.liste, pref = lire(cle);
      var ordre = (table.dataset.ordre || "0,asc").split(",");
      var dt = $(table).DataTable({
        sPaginationType: "full_numbers",
        responsive: false,
        pageLength: pref.longueur || 25,
        lengthMenu: [[10, 25, 50, 100, 200, 500, 1000, -1], ["10 lignes", "25 lignes", "50 lignes", "100 lignes", "200 lignes", "500 lignes", "1000 lignes", "Tout afficher"]],
        order: [pref.ordre || [parseInt(ordre[0], 10), ordre[1]]],
        dom: "<'barre_menu_dt_gauche'> <'d-flex flex-wrap justify-content-end dt-buttons-haut'<f><B>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'d-flex flex-wrap justify-content-between'<i><p>>",
        buttons: [
          {extend: "print", text: "Imprimer", title: table.dataset.titre, autoPrint: true, exportOptions: {columns: ":visible:not(.noexport)", format: FORMAT_EXPORT}},
          // Export rapide du contenu affiché (respecte le tri, le filtre et les colonnes visibles), sans les formules
          // du bouton "Exporter en Excel" du tableau de bord et du document (voir core/utils/export_xlsx.py).
          {extend: "excelHtml5", text: "Excel", title: table.dataset.titre, exportOptions: {columns: ":visible:not(.noexport)", format: FORMAT_EXPORT}},
          {extend: "colvis", text: "Colonnes", columns: ":not(.noexport)"},
          {extend: "pageLength", text: "Lignes"}
        ],
        columnDefs: [{orderable: false, searchable: false, targets: "noorder"}],
        language: $.extend(true, {}, LANGUE, {emptyTable: table.dataset.vide || LANGUE.emptyTable})
      });
      // Colonnes masquées : choix de l'utilisateur s'il en a fait un (bouton « Colonnes »), sinon masquage par défaut de la liste
      // Le nombre d'éléments affichés est annoncé aux lecteurs d'écran après une recherche ou un changement de page
      $(table).closest(".dataTables_wrapper").find(".dataTables_info").attr({"role": "status", "aria-live": "polite"});
      // Tableau défilant horizontalement sur petit écran : atteignable au clavier pour pouvoir le faire défiler
      $(table).parent().attr({"tabindex": "0", "role": "region", "aria-label": table.dataset.titre});
      if (Array.isArray(pref.masquees)) { dt.columns(pref.masquees).visible(false); }
      else { dt.columns(".masquee-par-defaut").visible(false); }
      function memoriser(cle_pref, valeur) { var p = lire(cle); p[cle_pref] = valeur; ecrire(cle, p); }
      // Textes coupés selon la largeur des colonnes : à recalculer après chaque affichage ou changement de colonnes
      if (window.marquerTextesCoupes) {
        dt.on("draw.dt column-visibility.dt", function () { setTimeout(function () { marquerTextesCoupes(table); }, 0); });
        marquerTextesCoupes(table);
      }
      dt.on("length.dt", function (e, settings, len) { memoriser("longueur", len); });
      dt.on("order.dt", function () { var o = dt.order(); if (o.length) { memoriser("ordre", o[0]); } });
      dt.on("column-visibility.dt", function () {
        var masquees = [];
        dt.columns().every(function (i) { if (!this.visible()) { masquees.push(i); } });
        memoriser("masquees", masquees);
      });
    });
  });
})(jQuery);
