<?php
if (!defined('ABSPATH')) exit;

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
    // Handle Manual Sync
    if (isset($_POST['visita_ai_run_sync']) && current_user_can('manage_options')) {
        check_admin_referer('visita_ai_sync_action', 'visita_ai_nonce');
        
        // This function is loaded from content-importer.php
        $result = visita_ai_fetch_latest_run();
        
        echo '<div class="notice notice-success"><p>' . wp_kses_post($result) . '</p></div>';
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