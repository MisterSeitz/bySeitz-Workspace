<?php
/**
 * Plugin Name: Visita AI Content Importer
 * Description: Automated Universal Content Importer (Modular).
 * Version: 2.0
 * Requires PHP: 7.4
 * Author: Visita
 * License: GPLv2 or later
 */

if (!defined('ABSPATH')) exit;

// 1. DEFINITIONS
define('VISITA_AI_ACTOR_ID', 'ObcP0K724GszDXGdp');
define('VISITA_AI_PATH', plugin_dir_path(__FILE__));

// 2. INCLUDES
// We load the logic first, then the UI
require_once VISITA_AI_PATH . 'includes/content-importer.php';

if (is_admin()) {
    require_once VISITA_AI_PATH . 'includes/admin-settings.php';
}

// 3. ACTIVATION HOOKS (Keep these in the main file)
register_activation_hook(__FILE__, 'visita_ai_activate_plugin');
function visita_ai_activate_plugin() {
    if (!wp_next_scheduled('visita_ai_hourly_event')) {
        wp_schedule_event(time(), 'hourly', 'visita_ai_hourly_event');
    }
}

register_deactivation_hook(__FILE__, 'visita_ai_deactivate_plugin');
function visita_ai_deactivate_plugin() {
    wp_clear_scheduled_hook('visita_ai_hourly_event');
}

// 4. CRON LINK
add_action('visita_ai_hourly_event', 'visita_ai_scheduled_sync');
function visita_ai_scheduled_sync() {
    if (get_option('visita_ai_auto_sync') !== 'yes') return;
    // Call the function from content-importer.php
    visita_ai_fetch_latest_run();
}