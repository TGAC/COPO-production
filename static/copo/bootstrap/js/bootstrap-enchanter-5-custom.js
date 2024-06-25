'use strict';

/**
 * ENCHANTER
 * Native JS/TS form wizard plugin for Bootstrap 5
 * Created by Brunno Pleffken Hosti
 * Repository: https://github.com/brunnopleffken/enchanter
 *
 * Slightly modified to accomodate the manifest qizard on
 */

class Enchanter {
  constructor(
    containerSelector,
    options = {},
    callbacks = {},
    isManifestWizard = false
  ) {
    this.options = {
      finishSelector: '[data-enchanter="finish"]',
      navItemSelector: '[data-bs-toggle="tab"]',
      nextSelector: '[data-enchanter="next"]',
      previousSelector: '[data-enchanter="previous"]',
    };

    this.callbacks = {
      onNext: null,
      onPrevious: null,
      onFinish: null,
    };

    Object.assign(this.options, options);
    Object.assign(this.callbacks, callbacks);
    this.container = document.getElementById(containerSelector);

    if (isManifestWizard) {
      this.containerActions = document.querySelector('.card-wizard-actions');
    }

    this.bootstrap();
  }

  next() {
    if (this.callbacks.onNext != null && this.callbacks.onNext() == false) {
      return false;
    }

    let nextElement = this.container.querySelector(
      '.nav .nav-link:nth-child(' + this.tabNextIndex + ')'
    );
    new bootstrap.Tab(nextElement).show();

    this.tabCurrentIndex = this.tabNextIndex;
    this.tabPreviousIndex = this.previousIndex();
    this.tabNextIndex = this.nextIndex();

    if (this.tabCurrentIndex > 1) {
      if (isManifestWizard) {
        if (
          this.containerActions.getAttribute(this.options.previousSelector) !=
          null
        ) {
          this.containerActions
            .querySelector(this.options.previousSelector)
            .removeAttribute('disabled');
        }
      } else {
        this.container
          .querySelector(this.options.previousSelector)
          .removeAttribute('disabled');
      }
    }

    if (this.tabNextIndex == null) {
      if (isManifestWizard) {
        this.containerActions
          .querySelector(this.options.nextSelector)
          .classList.add('d-none');

        if (
          this.containerActions.getAttribute(this.options.finishSelector) !=
          null
        ) {
          this.containerActions
            .querySelector(this.options.finishSelector)
            .classList.remove('d-none');
        }
      } else {
        this.container
          .querySelector(this.options.nextSelector)
          .classList.add('d-none');
        this.container
          .querySelector(this.options.finishSelector)
          .classList.remove('d-none');
      }
    }
  }

  previous() {
    if (
      this.callbacks.onPrevious != null &&
      this.callbacks.onPrevious() == false
    ) {
      return false;
    }

    let nextElement = this.container.querySelector(
      '.nav .nav-link:nth-child(' + this.tabPreviousIndex + ')'
    );
    new bootstrap.Tab(nextElement).show();

    this.tabCurrentIndex = this.tabPreviousIndex;
    this.tabPreviousIndex = this.previousIndex();
    this.tabNextIndex = this.nextIndex();

    if (this.tabPreviousIndex == null) {
      isManifestWizard
        ? null
        : this.container
            .querySelector(this.options.previousSelector)
            .setAttribute('disabled', 'disabled');
    }

    if (this.tabNextIndex != null) {
      if (isManifestWizard) {
        this.containerActions
          .querySelector(this.options.nextSelector)
          .classList.remove('d-none');

        if (
          this.containerActions.getAttribute(this.options.finishSelector) !=
          null
        ) {
          this.containerActions
            .querySelector(this.options.finishSelector)
            .classList.add('d-none');
        }
      } else {
        this.container
          .querySelector(this.options.nextSelector)
          .classList.remove('d-none');
        this.container
          .querySelector(this.options.finishSelector)
          .classList.add('d-none');
      }
    }
  }

  finish() {
    if (this.callbacks.onFinish != null && this.callbacks.onFinish() == false) {
      return false;
    }

    return true;
  }

  bootstrap() {
    this.tabCurrentIndex = this.currentIndex();
    this.tabNextIndex = this.nextIndex();

    if (isManifestWizard) {
      if (
        this.containerActions.getAttribute(this.options.previousSelector) !=
        null
      ) {
        this.containerActions
          .querySelector(this.options.previousSelector)
          .setAttribute('disabled', 'disabled');
      }

      if (
        this.containerActions.getAttribute(this.options.finishSelector) != null
      ) {
        this.containerActions
          .querySelector(this.options.finishSelector)
          .classList.add('d-none');
      }
    } else {
      this.container
        .querySelector(this.options.previousSelector)
        .setAttribute('disabled', 'disabled');
      this.container
        .querySelector(this.options.finishSelector)
        .classList.add('d-none');
    }

    this.addEventBindings();
  }

  addEventBindings() {
    if (isManifestWizard) {
      if (
        this.containerActions.getAttribute(this.options.previousSelector) !=
        null
      ) {
        this.containerActions
          .querySelector(this.options.previousSelector)
          .addEventListener('click', () => this.previous());
      }

      this.containerActions
        .querySelector(this.options.nextSelector)
        .addEventListener('click', () => this.next());

      if (
        this.containerActions.getAttribute(this.options.finishSelector) != null
      ) {
        this.containerActions
          .querySelector(this.options.finishSelector)
          .addEventListener('click', () => this.finish());
      }
    } else {
      this.container
        .querySelector(this.options.previousSelector)
        .addEventListener('click', () => this.previous());
      this.container
        .querySelector(this.options.nextSelector)
        .addEventListener('click', () => this.next());
      this.container
        .querySelector(this.options.finishSelector)
        .addEventListener('click', () => this.finish());
    }
  }

  getIndex(element) {
    return [...element.parentNode.children].findIndex((c) => c == element) + 1;
  }

  currentIndex() {
    return this.getIndex(this.container.querySelector('.nav .nav-link.active'));
  }

  nextIndex() {
    let nextIndexCandidate = this.tabCurrentIndex + 1;

    if (
      this.container.querySelector(
        '.nav .nav-link:nth-child(' + nextIndexCandidate + ')'
      ) == null
    ) {
      return null;
    }

    return nextIndexCandidate;
  }

  previousIndex() {
    let nextIndexCandidate = this.tabCurrentIndex - 1;

    if (
      this.container.querySelector(
        '.nav .nav-link:nth-child(' + nextIndexCandidate + ')'
      ) == null
    ) {
      return null;
    }

    return nextIndexCandidate;
  }
}