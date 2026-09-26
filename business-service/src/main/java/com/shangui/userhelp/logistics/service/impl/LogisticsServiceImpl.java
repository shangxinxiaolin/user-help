package com.shangui.userhelp.logistics.service.impl;

import com.shangui.userhelp.common.error.BusinessException;
import com.shangui.userhelp.common.error.ErrorCode;
import com.shangui.userhelp.logistics.domain.LogisticsInfo;
import com.shangui.userhelp.logistics.mapper.LogisticsMapper;
import com.shangui.userhelp.logistics.service.LogisticsService;
import org.springframework.stereotype.Service;

@Service
public class LogisticsServiceImpl implements LogisticsService {

    private final LogisticsMapper logisticsMapper;

    public LogisticsServiceImpl(LogisticsMapper logisticsMapper) {
        this.logisticsMapper = logisticsMapper;
    }

    @Override
    public LogisticsInfo query(String trackingNo) {
        if (trackingNo == null || trackingNo.isBlank()) {
            throw new BusinessException(ErrorCode.BAD_REQUEST, "tracking_no 不能为空");
        }
        LogisticsInfo info = logisticsMapper.findByTrackingNo(trackingNo);
        if (info == null) {
            throw new BusinessException(ErrorCode.NOT_FOUND, "没有找到物流信息");
        }
        return info;
    }
}
