// ============================================================================
// CGAL-SAFE WEASLEY CLOCK "SCISSOR-BLADE" HANDS (~50mm Pointer Length)
// Fixes "The given mesh is not closed!" by healing KellsFLF font contours in 2D
// and eliminating coplanar Z=0 3D boolean unions.
// ============================================================================

/* [Choose Hand to Render] */
hand_to_render = "richard_hand_2mm"; // ["all_preview", "richard_hand_2mm", "anna_hand_3mm", "esmae_hand_4mm", "cerys_hand_5mm"]

/* [Typography] */
name_font    = "KellsFLF:style=Bold"; 
initial_font = "Goudy Old Style:style=Bold";

/* [Pointer Lengths (Max <= 60mm, targeted around ~50mm)] */
len_richard = 55;
len_anna    = 55;
len_esmae   = 55;
len_cerys   = 55;

/* [Dimensions & Print Tolerances] */
bore_clearance  = 0.08; // Radial clearance for 2mm, 3mm, 4mm, 5mm brass tubes
blade_thickness = 2.0;  // Thickness of the hand (mm)
collet_height   = 4.0;  // Height of central hub on the brass shaft (mm)

$fn = 64;

// ============================================================================
// RENDER ROUTER
// ============================================================================
if (hand_to_render == "all_preview") {
    translate([  0, 0, 0]) weasley_filigree_hand("RICHARD", "R", 2.0 + bore_clearance, len_richard);
    translate([ 30, 0, 0]) weasley_filigree_hand("ANNA",    "A", 3.0 + bore_clearance, len_anna);
    translate([ 60, 0, 0]) weasley_filigree_hand("ESMAE",   "E", 4.0 + bore_clearance, len_esmae);
    translate([ 90, 0, 0]) weasley_filigree_hand("CERYS",   "C", 5.0 + bore_clearance, len_cerys);
} else if (hand_to_render == "richard_hand_2mm") {
    weasley_filigree_hand("RICHARD", "R", 2.0 + bore_clearance, len_richard);
} else if (hand_to_render == "anna_hand_3mm") {
    weasley_filigree_hand("ANNA",    "A", 3.0 + bore_clearance, len_anna);
} else if (hand_to_render == "esmae_hand_4mm") {
    weasley_filigree_hand("ESMAE",   "E", 4.0 + bore_clearance, len_esmae);
} else if (hand_to_render == "cerys_hand_5mm") {
    weasley_filigree_hand("CERYS",   "C", 5.0 + bore_clearance, len_cerys);
}

// ============================================================================
// 2D MODULE: ORNATE OFFSET SCISSOR FINGER-RING & INITIAL
// ============================================================================
module scissor_bow_2d(initial_str) {
    bow_cx = -3.4; // Offset to one side like a real half-scissor handle
    bow_cy = -21.0;
    
    translate([bow_cx, bow_cy]) {
        difference() {
            union() {
                // Main oval scissor bow outer loop
                scale([1.0, 1.28]) circle(r = 9.0);
                
                // Decorative beaded filigree scallops around the ring perimeter
                for (a = [0 : 18 : 342]) {
                    translate([8.9 * cos(a), 11.4 * sin(a)])
                        circle(r = 1.0);
                }
                // Side scroll finial
                translate([-9.4, 0]) circle(r = 1.6);
            }
            // Hollow inside of the oval finger loop
            scale([1.0, 1.28]) circle(r = 6.2);
        }

        // Ornate Initial in Goudy Old Style Bold
        // Note: offset() is applied AFTER scale() so Clipper cleans any self-intersecting font nodes
        offset(delta = 0.18, chamfer = true)
        scale([1.22, 1.48])
            text(initial_str, size = 11.0, font = initial_font, halign = "center", valign = "center", $fn = 32);
    }
}

// ============================================================================
// 2D MODULE: COMPACT ~50mm SCISSOR BLADE WITH THROUGH-CUT WINDOW & BRIDGED NAME
// ============================================================================
module scissor_blade_cutout_2d(name_str, hand_len) {
    win_start_y = 6.5;
    win_end_y   = hand_len - 11.5;
    win_len     = win_end_y - win_start_y;

    outer_half_w = 3.6;
    win_half_w   = 2.10;

    union() {
        // 1. Curved scissor neck from central pivot (0,0) to offset finger ring (-3.4, -21)
        hull() {
            circle(r = 3.8);
            translate([-1.3, -7.5])  circle(r = 2.7);
        }
        hull() {
            translate([-1.3, -7.5])  circle(r = 2.7);
            translate([-3.0, -13.5]) circle(r = 2.6);
        }
        // Decorative bolster collar above the finger bow
        translate([-2.2, -10.8]) scale([1.65, 0.7]) circle(r = 2.6);

        // 2. Main Scissor Blade with Open Through-Cut Window
        difference() {
            polygon(points = [
                [-3.4,   0.0],
                [-outer_half_w, 4.5],
                [-outer_half_w, win_end_y],
                [-2.0,  hand_len - 6.0],
                [ 0.0,  hand_len],
                [ 2.3,  hand_len - 6.0],
                [ outer_half_w + 0.3, win_end_y],
                [ outer_half_w + 0.5, 6.5],
                [ 3.5,   0.0]
            ]);

            // THROUGH-CUT WINDOW
            hull() {
                translate([0, win_start_y + 1.0]) circle(r = win_half_w);
                translate([0, win_end_y   - 1.0]) circle(r = win_half_w);
            }

            // Compact ornamental 4-point star & dot cutouts near the scissor tip
            translate([0, hand_len - 7.5]) rotate([0, 0, 45]) square([1.7, 1.7], center = true);
            translate([0, hand_len - 9.8]) circle(r = 0.6);
            translate([0, hand_len - 4.8]) circle(r = 0.55);
        }

        // 3. SOLID LETTERS IN KELLSFLF BRIDGING ACROSS THE COMPACT WINDOW
        n_chars = len(name_str);
        step_y  = (win_len - 1.6) / n_chars;
        char_along_blade_scale = min(0.95, step_y / 4.2);

        for (i = [0 : n_chars - 1]) {
            char_y = (win_start_y + 0.8) + (i + 0.5) * step_y;
            translate([0, char_y])
            rotate([0, 0, 90])
            // Apply offset(delta) AFTER scale() to sanitize KellsFLF self-intersections in 2D
            offset(delta = 0.14, chamfer = true)
            scale([char_along_blade_scale, 1.45])
                text(name_str[i], size = 3.5, font = name_font, halign = "center", valign = "center", $fn = 32);
        }
    }
}

// ============================================================================
// 2D MASTER SILHOUETTE (HEALED VIA CLIPPER BUFFER BEFORE 3D EXTRUSION)
// ============================================================================
module complete_hand_2d(name_str, initial_str, bore_d, collet_od, hand_len) {
    difference() {
        // Micro-buffer (+0.01 then -0.01) forces Clipper to merge any degenerate font vertices!
        offset(delta = 0.01)
        offset(delta = -0.01)
        union() {
            scissor_bow_2d(initial_str);
            scissor_blade_cutout_2d(name_str, hand_len);
            circle(d = collet_od + 1.2);
        }
        // Cut the central brass shaft hole in 2D so no 3D boolean subtraction is even needed!
        circle(d = bore_d);
    }
}

// ============================================================================
// MAIN 3D ASSEMBLY MODULE (ZERO 3D DIFFERENCES = 100% WATERTIGHT MANIFOLD)
// ============================================================================
module weasley_filigree_hand(name_str, initial_str, bore_d, hand_len) {
    collet_od = bore_d + 4.0;

    union() {
        // 1. Main 2.0mm thick Filigree Scissor Hand (with bore already cut in 2D)
        linear_extrude(height = blade_thickness, convexity = 20)
            complete_hand_2d(name_str, initial_str, bore_d, collet_od, hand_len);

        // 2. Decorative Scissor-Pivot Rim Boss (overlaps Z=1.9 to 2.4mm)
        translate([0, 0, blade_thickness - 0.1])
        linear_extrude(height = 0.5, convexity = 4)
        difference() {
            circle(d = collet_od + 1.2);
            circle(d = bore_d);
        }

        // 3. Central Pivot Collet up to 4.0mm (overlaps Z=1.9 to 4.0mm)
        translate([0, 0, blade_thickness - 0.1])
        linear_extrude(height = collet_height - blade_thickness + 0.1, convexity = 4)
        difference() {
            circle(d = collet_od);
            circle(d = bore_d);
        }
    }
}