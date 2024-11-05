/** @odoo-module */

import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";

export class PPMListRenderer extends ListRenderer {
    calculateColumnWidth(column) {
        const columnSizes = {
            mon_day: '65px',
            tue_day: '65px',
            wed_day: '65px',
            thu_day: '65px',
            fri_day: '65px',
            sat_day: '65px',
            week1: '65px',
            week2: '65px',
            week3: '65px',
            week4: '65px',
        };
        if (column.name in columnSizes) {
            return { type: 'absolute', value: columnSizes[column.name] };
        }

        return super.calculateColumnWidth(column);
    }
}

export class PPMX2ManyField extends X2ManyField {}

PPMX2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: PPMListRenderer,
};

registry.category("fields").add("ppm_one2many", PPMX2ManyField);