<?php
/**
 * Plugin Name: Visita AI Content Importer
 * Description: Automated Content Importer. Features Custom Intervals, Persistent Logging, and WooCommerce support.
 * Version: 3.1
 * Requires PHP: 7.4
 * Author: Visita
 * License: GPLv2 or later
 */

if (!defined('ABSPATH')) exit;

define('VISITA_AI_ACTOR_ID', 'ObcP0K724GszDXGdp'); 

// ======================================================
// 1. CUSTOM CRON SCHEDULE & ACTIVATION
// ======================================================

add_filter('cron_schedules', 'visita_ai_custom_schedule');
function visita_ai_custom_schedule($schedules) {
    $interval = (int) get_option('visita_ai_sync_interval', 60);
    if ($interval < 5) $interval = 60; 
    
    $schedules['visita_ai_custom'] = array(
        'interval' => $interval * 60, 
        'display'  => "Every $interval Minutes"
    );
    return $schedules;
}

register_activation_hook(__FILE__, 'visita_ai_activate_plugin');
function visita_ai_activate_plugin() {
    wp_clear_scheduled_hook('visita_ai_hourly_event');
    if (!wp_next_scheduled('visita_ai_hourly_event')) {
        wp_schedule_event(time(), 'visita_ai_custom', 'visita_ai_hourly_event');
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
// 2. SETTINGS & UI
// ======================================================

add_action('admin_menu', 'visita_ai_add_admin_menu');
function visita_ai_add_admin_menu() {
    add_options_page('Visita AI', 'Visita AI', 'manage_options', 'visita-ai-importer', 'visita_ai_options_page');
}

add_action('admin_init', 'visita_ai_settings_init');
function visita_ai_settings_init() {
    register_setting('visitaAiPlugin', 'visita_ai_apify_token', 'sanitize_text_field');
    register_setting('visitaAiPlugin', 'visita_ai_auto_sync', 'sanitize_text_field');
    register_setting('visitaAiPlugin', 'visita_ai_sync_interval', array(
        'type' => 'integer',
        'sanitize_callback' => 'visita_ai_reschedule_cron'
    ));
}

function visita_ai_reschedule_cron($input) {
    $new_minutes = absint($input);
    if ($new_minutes < 5) $new_minutes = 60; 
    
    $old_minutes = (int) get_option('visita_ai_sync_interval');
    if ($old_minutes !== $new_minutes) {
        wp_clear_scheduled_hook('visita_ai_hourly_event');
        wp_schedule_event(time(), 'visita_ai_custom', 'visita_ai_hourly_event');
    }
    return $new_minutes;
}

function visita_ai_options_page() {
    // 1. Handle Manual Sync
    if (isset($_POST['visita_ai_run_sync']) && current_user_can('manage_options')) {
        check_admin_referer('visita_ai_sync_action', 'visita_ai_nonce');
        $result = visita_ai_fetch_latest_run(); 
        echo '<div class="notice notice-info"><p>' . $result . '</p></div>';
    }

    // 2. Handle Clear Logs (NEW)
    if (isset($_POST['visita_ai_clear_logs']) && current_user_can('manage_options')) {
        check_admin_referer('visita_ai_clear_action', 'visita_ai_nonce');
        delete_option('visita_ai_last_log');
        delete_option('visita_ai_last_run_time');
        echo '<div class="notice notice-success"><p>Logs and history cleared successfully.</p></div>';
    }
    
    $last_log = get_option('visita_ai_last_log', '');
    $last_run_time = get_option('visita_ai_last_run_time', 'Never');
    ?>
    <div class="wrap">
        <h1>Visita AI Content Importer</h1>
        <form action="options.php" method="post">
            <?php settings_fields('visitaAiPlugin'); do_settings_sections('visitaAiPlugin'); ?>
            <table class="form-table">
                <tr><th>Apify API Token</th><td><input type="password" name="visita_ai_apify_token" value="<?php echo esc_attr(get_option('visita_ai_apify_token')); ?>" class="regular-text"></td></tr>
                <tr><th>Enable Auto Sync</th><td><label><input type="checkbox" name="visita_ai_auto_sync" value="yes" <?php checked(get_option('visita_ai_auto_sync'), 'yes'); ?>> Active</label></td></tr>
                <tr><th>Sync Interval</th><td><input type="number" name="visita_ai_sync_interval" value="<?php echo esc_attr(get_option('visita_ai_sync_interval', 60)); ?>" class="small-text"> minutes (Min: 5)</td></tr>
            </table>
            <?php submit_button(); ?>
        </form>
        
        <hr>
        <h2>Status & Logs</h2>
        <p><strong>Last Successful Run:</strong> <?php echo esc_html($last_run_time); ?></p>
        
        <div style="background: #f6f7f7; padding: 15px; border: 1px solid #c3c4c7; max-height: 300px; overflow-y: auto; margin-bottom: 15px;">
            <?php echo $last_log ? wp_kses_post($last_log) : '<em>No logs available.</em>'; ?>
        </div>

        <div style="display: flex; gap: 10px;">
            <form method="post">
                <?php wp_nonce_field('visita_ai_sync_action', 'visita_ai_nonce'); ?>
                <input type="submit" name="visita_ai_run_sync" class="button button-primary" value="Force Manual Sync">
            </form>

            <form method="post">
                <?php wp_nonce_field('visita_ai_clear_action', 'visita_ai_nonce'); ?>
                <input type="submit" name="visita_ai_clear_logs" class="button button-secondary" value="Clear Logs & History" onclick="return confirm('Are you sure you want to delete the logs?');">
            </form>
        </div>
    </div>
    <?php
}

// ======================================================
// 3. THE ENGINE (With Persistent Logging)
// ======================================================

function visita_ai_fetch_latest_run() {
    $token = get_option('visita_ai_apify_token');
    $actor_id = VISITA_AI_ACTOR_ID; 
    $logs = ""; 

    function vac_append($msg, &$logs) { 
        $line = "[" . date('H:i:s') . "] " . $msg . "<br>"; 
        $logs .= $line;
        return $line; 
    }

    vac_append("<strong>Starting Sync Process...</strong>", $logs);

    if (empty($token)) {
        $msg = vac_append("Error: API Token is missing.", $logs);
        update_option('visita_ai_last_log', $logs);
        return $msg;
    }

    $url = "https://api.apify.com/v2/acts/{$actor_id}/runs/last/dataset/items?token={$token}&status=SUCCEEDED";
    $response = wp_remote_get($url, array('timeout' => 30));

    if (is_wp_error($response)) {
        $msg = vac_append("API Connection Failed: " . $response->get_error_message(), $logs);
        update_option('visita_ai_last_log', $logs);
        return $msg;
    }

    $code = wp_remote_retrieve_response_code($response);
    if ($code !== 200) {
        $msg = vac_append("API Error (Code $code). Check Token or Apify logs.", $logs);
        update_option('visita_ai_last_log', $logs);
        return $msg;
    }
    
    $items = json_decode(wp_remote_retrieve_body($response), true);
    if (empty($items) || !is_array($items)) {
        $msg = vac_append("Connected, but dataset is empty.", $logs);
        update_option('visita_ai_last_log', $logs);
        return $msg;
    }

    require_once(ABSPATH . 'wp-admin/includes/media.php');
    require_once(ABSPATH . 'wp-admin/includes/file.php');
    require_once(ABSPATH . 'wp-admin/includes/image.php');

    $author_id = get_current_user_id();
    if ($author_id == 0) {
        $admins = get_users(['role'=>'administrator','number'=>1]);
        $author_id = !empty($admins) ? $admins[0]->ID : 1;
    }

    $imported = 0;

    foreach ($items as $item) {
        if (!is_array($item)) continue;
        
        $pt = !empty($item['post_type']) ? sanitize_key($item['post_type']) : 'post';
        $title = !empty($item['post_title']) ? sanitize_text_field($item['post_title']) : 'Untitled';

        if (!post_type_exists($pt)) {
            vac_append("Skipped '{$title}': Post Type '$pt' not found.", $logs);
            continue;
        }

        $existing = new WP_Query([
            'post_type' => $pt, 'title' => $title, 'post_status' => 'any', 
            'posts_per_page' => 1, 'fields' => 'ids'
        ]);

        if ($existing->have_posts()) {
            vac_append("Skipped '{$title}': Duplicate found.", $logs);
            continue;
        }

        $post_data = array(
            'post_title'    => $title,
            'post_content'  => !empty($item['post_content']) ? wp_kses_post($item['post_content']) : '',
            'post_status'   => !empty($item['post_status']) ? $item['post_status'] : 'publish',
            'post_type'     => $pt,
            'post_author'   => $author_id,
            'post_name'     => !empty($item['post_name']) ? sanitize_title($item['post_name']) : '',
            'post_excerpt'  => !empty($item['post_excerpt']) ? sanitize_textarea_field($item['post_excerpt']) : '',
        );
        if (!empty($item['post_date'])) $post_data['post_date'] = $item['post_date'];

        $post_id = wp_insert_post($post_data, true);
        
        if (is_wp_error($post_id)) {
            vac_append("Insert Failed: " . $post_id->get_error_message(), $logs);
            continue;
        }

        if ($pt === 'product' && function_exists('WC')) {
            visita_ai_process_woocommerce($post_id, $item);
        } elseif ($pt === 'job_listing') {
            visita_ai_process_mylisting($post_id, $item);
        } else {
            visita_ai_process_standard($post_id, $item);
        }

        visita_ai_process_images($post_id, $item);
        
        vac_append("✅ Imported: '{$title}' (ID: $post_id)", $logs);
        $imported++;
    }

    vac_append("<strong>Sync Finished. Total Imported: $imported</strong>", $logs);
    
    update_option('visita_ai_last_log', $logs);
    update_option('visita_ai_last_run_time', current_time('mysql'));

    return "Sync Complete. Check Logs below.";
}

// ======================================================
// 4. PROCESSORS (Standard, WC, MyListing, Images)
// ======================================================

function visita_ai_process_standard($post_id, $item) {
    if (!empty($item['taxonomies']) && is_array($item['taxonomies'])) {
        foreach ($item['taxonomies'] as $tax => $terms) {
            if (taxonomy_exists($tax)) wp_set_object_terms($post_id, $terms, $tax);
        }
    }
    if (!empty($item['meta']) && is_array($item['meta'])) {
        foreach ($item['meta'] as $key => $value) {
            update_post_meta($post_id, sanitize_key($key), $value);
        }
    }
}

function visita_ai_process_woocommerce($post_id, $item) {
    visita_ai_process_standard($post_id, $item);
    $product = wc_get_product($post_id);
    if (!$product) return;

    $meta = $item['meta'] ?? array();
    if (isset($meta['_price'])) {
        $product->set_regular_price($meta['_regular_price']);
        $product->set_price($meta['_price']);
    }
    if (isset($meta['_stock_status'])) {
        $product->set_stock_status($meta['_stock_status']);
    }
    $product->save();
}

function visita_ai_process_mylisting($post_id, $item) {
    visita_ai_process_standard($post_id, $item);
}

function visita_ai_process_images($post_id, $item) {
    if (!empty($item['featured_image'])) {
        $img_id = visita_ai_sideload_image($item['featured_image'], $post_id);
        if ($img_id) set_post_thumbnail($post_id, $img_id);
    }
    if (!empty($item['gallery_images']) && is_array($item['gallery_images'])) {
        $g_ids = [];
        foreach ($item['gallery_images'] as $url) {
            $gid = visita_ai_sideload_image($url, $post_id);
            if ($gid) $g_ids[] = $gid;
        }
        if (!empty($g_ids)) {
            update_post_meta($post_id, 'gallery_images', implode(',', $g_ids));
            update_post_meta($post_id, '_job_gallery', $g_ids);
            
            $post = get_post($post_id);
            if (strpos($post->post_content, '[gallery') === false) {
                $updated = $post->post_content . "\n" . '[gallery ids="' . implode(',', $g_ids) . '"]';
                wp_update_post(array('ID' => $post_id, 'post_content' => $updated));
            }
        }
    }
}

function visita_ai_sideload_image($url, $post_id) {
    if (filter_var($url, FILTER_VALIDATE_URL) === false) return false;
    $tmp = download_url($url);
    if (is_wp_error($tmp)) return false;
    
    $file = array('name' => basename(wp_parse_url($url, PHP_URL_PATH)), 'tmp_name' => $tmp);
    if (!pathinfo($file['name'], PATHINFO_EXTENSION)) $file['name'] .= '.jpg';
    
    $id = media_handle_sideload($file, $post_id);
    if (is_wp_error($id)) { @wp_delete_file($file['tmp_name']); return false; }
    return $id;
}