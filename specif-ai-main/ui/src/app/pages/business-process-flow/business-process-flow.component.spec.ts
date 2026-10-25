import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BusinessProcessFlowComponent } from './business-process-flow.component';

describe('BusinessProcessFlowComponent', () => {
  let component: BusinessProcessFlowComponent;
  let fixture: ComponentFixture<BusinessProcessFlowComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [BusinessProcessFlowComponent]
    });
    fixture = TestBed.createComponent(BusinessProcessFlowComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
