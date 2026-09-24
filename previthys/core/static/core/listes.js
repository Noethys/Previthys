/*
 * -*- coding: utf-8 -*-
 * Copyright (c) 2026 Ivan LUCAS.
 * Previthys, application de gestion du DUERP (Document Unique d’Évaluation des Risques Professionnels).
 * Distribué sous licence GNU GPL.
 */

/* Initialisation des listes DataTables.
   Le tri, le nombre de lignes et les colonnes masquées sont mémorisés par liste dans le navigateur. */
(function ($) {
  var LANGUE = {
    buttons: {colvis: "Colonnes", excel: "Excel", copy: "Copier", pageLength: {"-1": "Tout afficher", _: "Afficher %d lignes"}},
    processing: "Traitement en cours...", search: "", searchPlaceholder: "Rechercher",
    lengthMenu: "Afficher _MENU_ éléments",
    info: "Affichage de l'élément _START_ à _END_ sur _TOTAL_ éléments",
    infoEmpty: "Affichage de l'élément 0 à 0 sur 0 éléments",
    infoFiltered: "(filtré de _MAX_ éléments au total)",
    loadingRecords: "Chargement en cours...", zeroRecords: "Aucun élément à afficher", emptyTable: "Aucune donnée",
    paginate: {first: "Premier", previous: "Précédent", next: "Suivant", last: "Dernier"},
    aria: {sortAscending: ": activer pour trier la colonne par ordre croissant", sortDescending: ": activer pour trier la colonne par ordre décroissant"}
  };

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
          {extend: "print", text: "Imprimer", title: table.dataset.titre, autoPrint: true, exportOptions: {columns: ":visible:not(.noexport)"}},
          // Export rapide du contenu affiché (respecte le tri, le filtre et les colonnes visibles), sans les formules
          // du bouton "Exporter en Excel" du tableau de bord et du document (voir core/utils/export_xlsx.py).
          {extend: "excelHtml5", text: "Excel", title: table.dataset.titre, exportOptions: {columns: ":visible:not(.noexport)"}},
          {extend: "colvis", text: "Colonnes", columns: ":not(.noexport)"},
          {extend: "pageLength", text: "Lignes"}
        ],
        columnDefs: [{orderable: false, searchable: false, targets: "noorder"}],
        language: $.extend(true, {}, LANGUE, {emptyTable: table.dataset.vide || LANGUE.emptyTable})
      });
      if (pref.masquees && pref.masquees.length) { dt.columns(pref.masquees).visible(false); }
      function memoriser(cle_pref, valeur) { var p = lire(cle); p[cle_pref] = valeur; ecrire(cle, p); }
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
