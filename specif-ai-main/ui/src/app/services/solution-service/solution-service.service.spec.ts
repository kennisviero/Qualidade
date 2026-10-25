import { TestBed } from '@angular/core/testing';

import { SolutionServiceService } from './solution-service.service';

describe('SolutionServiceService', () => {
  let service: SolutionServiceService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SolutionServiceService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
