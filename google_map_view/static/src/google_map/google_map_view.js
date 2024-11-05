/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { GoogleMapArchParser } from "./google_map_arch_parser";
import { GoogleMapModel } from "./google_map_model";
import { GoogleMapController } from "./google_map_controller";
import { GoogleMapRenderer } from "./google_map_renderer";

export const mapView = {
    type: "google_map_view",
    display_name: _lt("Google Map"),
    icon: "fa fa-map-marker",
    multiRecord: true,
    isMobileFriendly: true,
    Controller: GoogleMapController,
    Renderer: GoogleMapRenderer,
    Model: GoogleMapModel,
    ArchParser: GoogleMapArchParser,
    buttonTemplate:  "google_map_view.MapView.Buttons",

    props: (genericProps, view, config) => {
        let modelParams = genericProps.state;
        if (!modelParams) {
            const { arch,  resModel, fields, context} = genericProps;
            const parser = new view.ArchParser();
            const archInfo = parser.parse(arch);
            const views = config.views || [];
            modelParams = {
                context: context,
                showFilter: archInfo.showFilter,
                defaultOrder: archInfo.defaultOrder,
                fieldNames: archInfo.fieldNames,
                fieldNamesMarkerPopup: archInfo.fieldNamesMarkerPopup,
                fields: fields,
                hasFormView: views.some((view) => view[1] === "form"),
                hideAddress: archInfo.hideAddress || false,
                hideName: archInfo.hideName || false,
                hideTitle: archInfo.hideTitle || false,
                limit: archInfo.limit || 80,
                numbering: archInfo.routing || false,
                offset: 0,
                panelTitle:
                    archInfo.panelTitle || config.getDisplayName() || _lt("Items"),
                resModel: resModel,
                resPartnerField: archInfo.resPartnerField,
                routing: archInfo.routing || false,
            };
        }

        return {
            ...genericProps,
            Model: view.Model,
            modelParams,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
        };
    },
};

registry.category("views").add("google_map_view", mapView);
