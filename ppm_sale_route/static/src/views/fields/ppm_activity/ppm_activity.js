/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

import { CharField } from "@web/views/fields/char_field";

export class PPMSaleActivty extends CharField {
    setup(){
        super.setup()
        console.log('Loaded');
    }
}

PPMSaleActivty.supportedTypes = ["char"]

registry.category("fields").add("ppm_sale_activity", PPMSaleActivty)
