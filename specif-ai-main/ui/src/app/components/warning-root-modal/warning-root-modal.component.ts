import { Component, OnInit } from '@angular/core';
import { MatDialogRef } from '@angular/material/dialog';
import { APP_CONSTANTS } from 'src/app/constants/app.constants';
import { ButtonComponent } from '../core/button/button.component';

@Component({
  selector: 'app-warning-root-modal',
  templateUrl: './warning-root-modal.component.html',
  styleUrls: ['./warning-root-modal.component.scss'],
  standalone: true,
  imports: [ButtonComponent],
})
export class WarningRootModalComponent implements OnInit {
  workingDir: string | null | undefined;

  constructor(private modalRef: MatDialogRef<WarningRootModalComponent>) {}

  ngOnInit() {
    this.workingDir = localStorage.getItem(APP_CONSTANTS.WORKING_DIR);
  }

  openFolderSelector() {
    this.modalRef.close(true);
  }

  // closeModal() {
  //   this.modalRef.close(false);
  // }
}
