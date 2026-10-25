import { Component, OnInit } from '@angular/core';
import {
  trigger,
  state,
  style,
  animate,
  transition,
} from '@angular/animations';
import { AlertService } from '../../../services/alert.service';
import { NgIf } from '@angular/common';
import { NgIconComponent } from '@ng-icons/core';

@Component({
  selector: 'app-alert',
  templateUrl: './alert.component.html',
  styleUrls: ['./alert.component.scss'],
  standalone: true,
  animations: [
    trigger('fadeInOut', [
      state(
        'void',
        style({
          opacity: 0,
          transform: 'translateY(-20px)',
        }),
      ),
      transition('void <=> *', [animate('300ms ease-in-out')]),
    ]),
  ],
  imports: [NgIf, NgIconComponent],
})
export class AlertComponent implements OnInit {
  message: string = '';
  isVisible: boolean = false;

  constructor(private alertService: AlertService) {}

  ngOnInit() {
    this.alertService.currentMessage.subscribe(
      (message) => (this.message = message),
    );
    this.alertService.currentVisibility.subscribe(
      (isVisible) => (this.isVisible = isVisible),
    );
  }

  closeAlert() {
    this.alertService.hideAlert();
  }
}
