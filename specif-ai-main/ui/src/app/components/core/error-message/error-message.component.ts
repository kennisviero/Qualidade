import { Component, Input } from '@angular/core';
import { FORM_ERROR_MESSAGES } from '../../../constants/messages.constants';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-error-message',
  templateUrl: './error-message.component.html',
  styleUrls: ['./error-message.component.scss'],
  standalone: true,
  imports: [NgIf],
})
export class ErrorMessageComponent {
  @Input() errorControl!: any;

  get errorMessages() {
    const { errors } = this.errorControl;
    if (!errors) {
      return;
    }
    const errorKeys = Object.keys(errors);
    const errorMessages = errorKeys.map((key) => {
      return FORM_ERROR_MESSAGES[key];
    });
    return errorMessages.join(', ');
  }
}
