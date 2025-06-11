import * as flsFunctions from "./modules/functions.js";
import * as sideBar from "./modules/sideBar.js";
import * as navMenu from "./modules/navMenu.js";
import * as langSwitcher from "./modules/langSwitcher.js";
import { setupProductFilters } from './modules/tagFilters.js';
import { enableSubmitWhenAllRequiredFieldsFilled } from './modules/enableSubmit.js';
import { setupContentToggle } from './modules/contentToggle.js';
import { setupCartButtons } from './modules/cartButtons.js';
import { setupTariffSelect } from './modules/tariffSelect.js';
import { initTabs } from './modules/tabs.js';
import { toggleDescription } from './modules/descriptionToggle.js';
import { setupCopyLink } from './modules/copyLink.js';
import { setupGenCopy } from './modules/copyGen.js';
import { initRatingStars } from './modules/ratingStars.js';
import { autoResizeTextareas } from './modules/autoTextarea.js';
import { setupFilterTabs } from './modules/filterTabs.js';
import { initTrafficCharts } from './modules/trafficCharts.js';
import { initCart } from './modules/cart.js';
import { initDropdown } from "./modules/dropdown.js";
import { plusMinus } from "./modules/plusMinus.js";
import { initAuth } from "./modules/newAuth.js";
import * as modals from "./modules/modals.js";

// initAuth();

function handleError(func, logError = false) {
    try {
        func();
    } catch (e) {
        logError && console.log(e);
    }
}

handleError(setupProductFilters);
handleError(enableSubmitWhenAllRequiredFieldsFilled);
handleError(setupContentToggle);
handleError(setupCartButtons);
handleError(setupTariffSelect);
handleError(initTabs);
handleError(setupFilterTabs);
handleError(toggleDescription);
handleError(setupCopyLink);
handleError(initRatingStars);
handleError(autoResizeTextareas);
handleError(initTrafficCharts);
handleError(setupGenCopy);
handleError(initCart);
handleError(initDropdown);
handleError(plusMinus);