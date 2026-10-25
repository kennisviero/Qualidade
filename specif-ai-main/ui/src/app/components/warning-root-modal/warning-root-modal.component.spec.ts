import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WarningRootModalComponent } from './warning-root-modal.component';

describe('WarningRootModalComponent', () => {
  let component: WarningRootModalComponent;
  let fixture: ComponentFixture<WarningRootModalComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [WarningRootModalComponent]
    });
    fixture = TestBed.createComponent(WarningRootModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
