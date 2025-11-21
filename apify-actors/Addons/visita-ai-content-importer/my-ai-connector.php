<?php
/**
 * Plugin Name: Visita AI Content Importer
 * Description: Automated Universal Content Importer. Connects to Apify to pull Posts, Products, and Listings automatically.
 * Version: 1.0
 * Requires PHP: 7.4
 * Author: Visita
 * License: GPLv2 or later
 */

if (!defined('ABSPATH')) exit;

// HARDCODED SERVICE ID
define('VISITA_AI_ACTOR_ID', 'ObcP0K724GszDXGdp'); 

// ======================================================
// 1. CRON & ACTIVATION HOOKS
// ======================================================

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

add_action('visita_ai_hourly_event', 'visita_ai_scheduled_sync');

function visita_ai_scheduled_sync() {
    if (get_option('visita_ai_auto_sync') !== 'yes') return;
    visita_ai_fetch_latest_run();
}

// ======================================================
// 2. SETTINGS & MENU
// ======================================================

add_action('admin_menu', 'visita_ai_add_admin_menu');
function visita_ai_add_admin_menu() {
    add_options_page('Visita AI', 'Visita AI', 'manage_options', 'visita-ai-importer', 'visita_ai_options_page');
}

add_action('admin_init', 'visita_ai_settings_init');
function visita_ai_settings_init() {
    register_setting('visitaAiPlugin', 'visita_ai_apify_token', 'sanitize_text_field');
    register_setting('visitaAiPlugin', 'visita_ai_auto_sync', 'sanitize_text_field');
}

function visita_ai_options_page() {
    // SECURITY FIX: Nonce Verification
    if (isset($_POST['visita_ai_run_sync']) && current_user_can('manage_options')) {
        check_admin_referer('visita_ai_sync_action', 'visita_ai_nonce');
        $result = visita_ai_fetch_latest_run();
        echo '<div class="notice notice-success"><p>' . esc_html($result) . '</p></div>';
    }
    ?>
    <div class="wrap">
        <h1>Visita AI Content Importer</h1>
        <form action="options.php" method="post">
            <?php settings_fields('visitaAiPlugin'); do_settings_sections('visitaAiPlugin'); ?>
            <table class="form-table">
                <tr>
                    <th scope="row">Apify API Token</th>
                    <td>
                        <input type="password" name="visita_ai_apify_token" value="<?php echo esc_attr(get_option('visita_ai_apify_token')); ?>" class="regular-text">
                        <p class="description">Get your API Token from the <a href="https://console.apify.com/account/integrations" target="_blank">Apify Console</a>.</p>
                    </td>
                </tr>
                <tr>
                    <th scope="row">Automatic Sync</th>
                    <td>
                        <label>
                            <input type="checkbox" name="visita_ai_auto_sync" value="yes" <?php checked(get_option('visita_ai_auto_sync'), 'yes'); ?>>
                            Enable Hourly Sync
                        </label>
                    </td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
        <hr>
        <h2>Manual Override</h2>
        <form method="post">
            <?php wp_nonce_field('visita_ai_sync_action', 'visita_ai_nonce'); ?>
            <input type="submit" name="visita_ai_run_sync" class="button button-primary" value="Fetch Latest Content Now">
        </form>
    </div>
    <?php
}

// ======================================================
// 3. THE UNIVERSAL FETCHER
// ======================================================

function visita_ai_fetch_latest_run() {
    $token = get_option('visita_ai_apify_token');
    $actor_id = VISITA_AI_ACTOR_ID; 

    if (empty($token)) return "Error: Missing API Token.";

    $url = "https://api.apify.com/v2/acts/{$actor_id}/runs/last/dataset/items?token={$token}&status=SUCCEEDED";
    $response = wp_remote_get($url, array('timeout' => 30));

    if (is_wp_error($response)) return "Connection Error: " . $response->get_error_message();
    
    $items = json_decode(wp_remote_retrieve_body($response), true);
    if (empty($items)) return "Connected, but no data found.";

    require_once(ABSPATH . 'wp-admin/includes/media.php');
    require_once(ABSPATH . 'wp-admin/includes/file.php');
    require_once(ABSPATH . 'wp-admin/includes/image.php');

    $count = 0;

    foreach ($items as $item) {
        $pt = isset($item['post_type']) ? sanitize_key($item['post_type']) : 'post';
        $title = sanitize_text_field($item['post_title']);

        // Duplication Check
        $existing_query = new WP_Query(array(
            'post_type'      => $pt,
            'title'          => $title,
            'post_status'    => 'any',
            'posts_per_page' => 1,
            'fields'         => 'ids'
        ));
        if ($existing_query->have_posts()) continue;

        // --- WP ALL IMPORT STYLE MAPPING ---
        $post_data = array(
            'post_title'    => $title,
            'post_content'  => wp_kses_post($item['post_content']),
            'post_type'     => $pt,
            // Advanced Options
            'post_status'   => isset($item['post_status']) ? $item['post_status'] : 'publish',
            'post_name'     => isset($item['post_name']) ? sanitize_title($item['post_name']) : '', // Slug
            'post_excerpt'  => isset($item['post_excerpt']) ? sanitize_textarea_field($item['post_excerpt']) : '',
            'post_author'   => isset($item['post_author']) ? absint($item['post_author']) : 1,
            'post_date'     => isset($item['post_date']) ? $item['post_date'] : '', // WP handles validation
            'comment_status'=> isset($item['comment_status']) ? $item['comment_status'] : 'closed',
        );
        
        $post_id = wp_insert_post($post_data);
        if (is_wp_error($post_id)) continue;

        // Handle Taxonomies
        if (!empty($item['taxonomies']) && is_array($item['taxonomies'])) {
            foreach ($item['taxonomies'] as $taxonomy => $terms) {
                if (taxonomy_exists($taxonomy)) wp_set_object_terms($post_id, $terms, $taxonomy);
            }
        }

        // Handle Custom Meta
        if (!empty($item['meta']) && is_array($item['meta'])) {
            foreach ($item['meta'] as $key => $value) {
                update_post_meta($post_id, sanitize_key($key), $value);
            }
        }

        // Handle Featured Image
        if (!empty($item['featured_image'])) {
            $image_id = visita_ai_sideload_image($item['featured_image'], $post_id);
            if ($image_id) set_post_thumbnail($post_id, $image_id);
        }

        // Handle Galleries
        if (!empty($item['gallery_images']) && is_array($item['gallery_images'])) {
            $gallery_ids = [];
            foreach ($item['gallery_images'] as $img_url) {
                $gid = visita_ai_sideload_image($img_url, $post_id);
                if ($gid) $gallery_ids[] = $gid;
            }
            if (!empty($gallery_ids)) {
                 update_post_meta($post_id, 'gallery_images', implode(',', $gallery_ids)); 
                 $shortcode = '[gallery ids="' . implode(',', $gallery_ids) . '"]';
                 $update_post = array('ID' => $post_id, 'post_content' => $item['post_content'] . "\n" . $shortcode);
                 wp_update_post($update_post);
            }
        }
        $count++;
    }
    return "Success! Imported $count items.";
}

function visita_ai_sideload_image($url, $post_id) {
    if (filter_var($url, FILTER_VALIDATE_URL) === false) return false;
    $tmp = download_url($url);
    if (is_wp_error($tmp)) return false;
    
    // COMPLIANCE FIX: Use wp_parse_url instead of parse_url
    $file_array = array('name' => basename(wp_parse_url($url, PHP_URL_PATH)), 'tmp_name' => $tmp);
    
    if (!pathinfo($file_array['name'], PATHINFO_EXTENSION)) $file_array['name'] .= '.jpg';
    $id = media_handle_sideload($file_array, $post_id);
    
    // COMPLIANCE FIX: Use wp_delete_file instead of unlink
    if (is_wp_error($id)) { 
        @wp_delete_file($file_array['tmp_name']); 
        return false; 
    }
    return $id;
}