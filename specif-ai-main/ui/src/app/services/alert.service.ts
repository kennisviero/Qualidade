import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AlertService {
  private alertMessageSource = new BehaviorSubject<string>('');
  private alertVisibilitySource = new BehaviorSubject<boolean>(false);

  currentMessage = this.alertMessageSource.asObservable();
  currentVisibility = this.alertVisibilitySource.asObservable();

  showAlert(message: string, duration: number = 5000) {
    this.alertMessageSource.next(message);
    this.alertVisibilitySource.next(true);
    // setTimeout(() => {
    //   this.hideAlert();
    // }, duration);
  }

  hideAlert() {
    this.alertVisibilitySource.next(false);
  }
}
