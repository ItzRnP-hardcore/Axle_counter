#include <errno.h>
#include <dirent.h>
#include <stdlib.h>
#include "esp_log.h"
#include "esp_check.h"
#include "driver/gpio.h"
#include "tinyusb.h"
#include "tinyusb_default_config.h"
#include "tinyusb_msc.h"
#include "sdmmc_cmd.h"
#include "diskio_impl.h"
#include "diskio_sdmmc.h"

static const char *TAG = "msc_sd_app";
tinyusb_msc_storage_handle_t storage_hdl = NULL;

/* TinyUSB descriptors setup */
#define EPNUM_MSC       1
#define TUSB_DESC_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_MSC_DESC_LEN)

enum {
    ITF_NUM_MSC = 0,
    ITF_NUM_TOTAL
};

enum {
    EDPT_CTRL_OUT = 0x00,
    EDPT_CTRL_IN  = 0x80,

    EDPT_MSC_OUT  = 0x01,
    EDPT_MSC_IN   = 0x81,
};

static tusb_desc_device_t descriptor_config = {
    .bLength = sizeof(descriptor_config),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = 0x303A, // Espressif VID
    .idProduct = 0x4002,
    .bcdDevice = 0x100,
    .iManufacturer = 0x01,
    .iProduct = 0x02,
    .iSerialNumber = 0x03,
    .bNumConfigurations = 0x01
};

static uint8_t const msc_fs_configuration_desc[] = {
    // Config number, interface count, string index, total length, attribute, power in mA
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, TUSB_DESC_TOTAL_LEN, TUSB_DESC_CONFIG_ATT_REMOTE_WAKEUP, 100),
    // Interface number, string index, EP Out & EP In address, EP size
    TUD_MSC_DESCRIPTOR(ITF_NUM_MSC, 0, EDPT_MSC_OUT, EDPT_MSC_IN, 64),
};

static char const *string_desc_arr[] = {
    (const char[]) { 0x09, 0x04 },  // 0: English
    "TinyUSB",                      // 1: Manufacturer
    "TinyUSB Device",               // 2: Product
    "123456",                       // 3: Serials
    "Example MSC",                  // 4. MSC
};

/* SD Card Initialization */
static esp_err_t storage_init_sdmmc(sdmmc_card_t **card)
{
    esp_err_t ret = ESP_OK;
    sdmmc_card_t *sd_card;

    ESP_LOGI(TAG, "Initializing SDCard via SDMMC");

    sdmmc_host_t host = SDMMC_HOST_DEFAULT();
    sdmmc_slot_config_t slot_config = SDMMC_SLOT_CONFIG_DEFAULT();
    
    // IMPORTANT: Set this to 1 if your SD card reader uses a 1-bit bus (SPI-like), 
    // or 4 for standard SDMMC (4-bit data bus).
    slot_config.width = 4; 
    
    // IMPORTANT: Update these GPIO pins to match your ESP32-S3's SD Card reader connection!
    slot_config.clk = 39;
    slot_config.cmd = 38;
    slot_config.d0  = 40;
    slot_config.d1  = 41;
    slot_config.d2  = 42;
    slot_config.d3  = 43;
    
    slot_config.flags |= SDMMC_SLOT_FLAG_INTERNAL_PULLUP;

    sd_card = (sdmmc_card_t *)malloc(sizeof(sdmmc_card_t));
    if (!sd_card) return ESP_ERR_NO_MEM;

    ESP_ERROR_CHECK((*host.init)());
    ESP_ERROR_CHECK(sdmmc_host_init_slot(host.slot, (const sdmmc_slot_config_t *) &slot_config));

    while (sdmmc_card_init(&host, sd_card)) {
        ESP_LOGE(TAG, "Insert SD card or check wiring. Retrying in 3 seconds...");
        vTaskDelay(pdMS_TO_TICKS(3000));
    }

    sdmmc_card_print_info(stdout, sd_card);
    *card = sd_card;

    return ESP_OK;
}


void app_main(void)
{
    ESP_LOGI(TAG, "Initializing storage...");

    // Configure MSC Storage
    tinyusb_msc_storage_config_t storage_cfg = {
        // Mount point set directly to USB so it appears immediately in PC File Explorer!
        .mount_point = TINYUSB_MSC_STORAGE_MOUNT_USB,
        .fat_fs = {
            .base_path = NULL,
            .config.max_files = 5,
            .format_flags = 0,
        },
    };

    // Initialize SD Card
    static sdmmc_card_t *card = NULL;
    ESP_ERROR_CHECK(storage_init_sdmmc(&card));
    
    // Assign SD Card to TinyUSB Storage
    storage_cfg.medium.card = card;
    ESP_ERROR_CHECK(tinyusb_msc_new_storage_sdmmc(&storage_cfg, &storage_hdl));

    ESP_LOGI(TAG, "Initializing TinyUSB MSC Driver...");

    tinyusb_config_t tusb_cfg = TINYUSB_DEFAULT_CONFIG();
    tusb_cfg.descriptor.device = &descriptor_config;
    tusb_cfg.descriptor.full_speed_config = msc_fs_configuration_desc;
    tusb_cfg.descriptor.string = string_desc_arr;
    tusb_cfg.descriptor.string_count = sizeof(string_desc_arr) / sizeof(string_desc_arr[0]);

    // Install TinyUSB Driver
    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));

    ESP_LOGI(TAG, "Done! The ESP32-S3 should now appear as a USB Drive on your PC.");
    
    // Idle loop
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
